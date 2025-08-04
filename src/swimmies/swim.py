"""
SWIM Protocol Implementation for Swimmies Library

This module implements the SWIM (Scalable Weakly-consistent Infection-style Process
Group Membership) protocol for distributed node membership and failure detection.

SWIM Features:
- Scalable failure detection via gossip protocol
- Infection-style dissemination of membership updates
- Probabilistic failure detection with configurable timeouts
- Anti-entropy mechanisms for membership consistency
"""

import json
import logging
import random
import socket
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .discovery import NodeInfo


class MembershipState(Enum):
    """Node membership states in SWIM protocol"""

    ALIVE = "alive"
    SUSPECT = "suspect"
    FAILED = "failed"
    LEFT = "left"


class MessageType(Enum):
    """SWIM protocol message types"""

    PING = "ping"
    PING_REQ = "ping_req"
    ACK = "ack"
    SUSPECT = "suspect"
    CONFIRM = "confirm"
    ALIVE = "alive"
    JOIN = "join"
    LEAVE = "leave"
    SYNC = "sync"  # For DNS record synchronization


@dataclass
class MembershipUpdate:
    """Represents a membership state change to be gossiped"""

    node_id: str
    state: MembershipState
    incarnation: int  # Logical timestamp for conflict resolution
    timestamp: float
    source_node: str  # Node that originated this update


@dataclass
class SwimMessage:
    """SWIM protocol message structure"""

    type: MessageType
    sender_id: str
    target_id: Optional[str] = None
    incarnation: int = 0
    timestamp: float = 0.0
    payload: Optional[Dict[str, Any]] = None
    piggyback_updates: List[MembershipUpdate] = None

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.piggyback_updates is None:
            self.piggyback_updates = []


@dataclass
class SwimMember:
    """SWIM protocol member information"""

    node_info: NodeInfo
    state: MembershipState
    incarnation: int
    last_update: float
    suspect_timeout: Optional[float] = None
    failure_count: int = 0

    @property
    def is_alive(self) -> bool:
        return self.state == MembershipState.ALIVE

    @property
    def is_suspect(self) -> bool:
        return self.state == MembershipState.SUSPECT

    @property
    def is_failed(self) -> bool:
        return self.state == MembershipState.FAILED


class SwimProtocol:
    """
    SWIM Protocol implementation for distributed membership management

    This class implements the core SWIM protocol with gossip-based membership
    updates, failure detection, and DNS record synchronization capabilities.
    """

    def __init__(
        self,
        node_info: NodeInfo,
        port: int = 8888,
        protocol_interval: float = 1.0,
        suspect_timeout: float = 5.0,
        failure_timeout: float = 10.0,
        gossip_factor: int = 3,
        max_piggyback: int = 10,
    ):
        self.node_info = node_info
        self.port = port
        self.protocol_interval = protocol_interval
        self.suspect_timeout = suspect_timeout
        self.failure_timeout = failure_timeout
        self.gossip_factor = gossip_factor  # Number of nodes to gossip to
        self.max_piggyback = max_piggyback  # Max updates to piggyback

        # Protocol state
        self.members: Dict[str, SwimMember] = {}
        self.incarnation = 0  # Our current incarnation number
        self.running = False
        self.socket: Optional[socket.socket] = None

        # Threading
        self.protocol_thread: Optional[threading.Thread] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()

        # Gossip state
        self.pending_updates: List[MembershipUpdate] = []
        self.update_counts: Dict[str, int] = {}  # Track gossip spread

        # Callbacks
        self.member_joined_callback: Optional[Callable[[NodeInfo], None]] = None
        self.member_left_callback: Optional[Callable[[NodeInfo], None]] = None
        self.member_failed_callback: Optional[Callable[[NodeInfo], None]] = None
        self.dns_sync_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        # DNS record state for synchronization
        self.dns_records: Dict[str, Any] = {}
        self.dns_version: int = 0

        self.logger = logging.getLogger(f"swim.{self.node_info.node_id}")

    def start(self):
        """Start the SWIM protocol"""
        if self.running:
            return

        self.running = True
        self.incarnation = int(time.time())  # Initialize incarnation

        # Create UDP socket for SWIM communication
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("0.0.0.0", self.port))

        # Add ourselves to the membership
        with self.lock:
            self.members[self.node_info.node_id] = SwimMember(
                node_info=self.node_info,
                state=MembershipState.ALIVE,
                incarnation=self.incarnation,
                last_update=time.time(),
            )

        # Start protocol threads
        self.listener_thread = threading.Thread(
            target=self._message_listener, daemon=True
        )
        self.protocol_thread = threading.Thread(target=self._protocol_loop, daemon=True)

        self.listener_thread.start()
        self.protocol_thread.start()

        self.logger.info(f"SWIM protocol started on port {self.port}")

    def stop(self):
        """Stop the SWIM protocol"""
        if not self.running:
            return

        self.running = False

        # Send leave message to other nodes
        self._broadcast_leave()

        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None

        # Wait for threads to finish
        if self.protocol_thread and self.protocol_thread.is_alive():
            self.protocol_thread.join(timeout=2.0)
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)

        self.logger.info("SWIM protocol stopped")

    def join_cluster(self, seed_nodes: List[str]):
        """Join a SWIM cluster via seed nodes"""
        for seed_address in seed_nodes:
            try:
                host, port = seed_address.split(":")
                port = int(port)

                # Send join message
                join_msg = SwimMessage(
                    type=MessageType.JOIN,
                    sender_id=self.node_info.node_id,
                    payload={"node_info": asdict(self.node_info)},
                )

                self._send_message(join_msg, host, port)
                self.logger.info(f"Sent join request to {seed_address}")

            except Exception as e:
                self.logger.error(f"Failed to join via seed {seed_address}: {e}")

    def add_dns_record(self, name: str, record_data: Any):
        """Add/update a DNS record for synchronization"""
        with self.lock:
            self.dns_records[name] = record_data
            self.dns_version += 1

        # Trigger DNS sync gossip
        self._gossip_dns_sync()

    def remove_dns_record(self, name: str):
        """Remove a DNS record"""
        with self.lock:
            if name in self.dns_records:
                del self.dns_records[name]
                self.dns_version += 1

        # Trigger DNS sync gossip
        self._gossip_dns_sync()

    def get_alive_members(self) -> List[NodeInfo]:
        """Get list of alive cluster members"""
        with self.lock:
            return [
                member.node_info for member in self.members.values() if member.is_alive
            ]

    def get_member_count(self) -> Dict[str, int]:
        """Get count of members by state"""
        with self.lock:
            counts = {state.value: 0 for state in MembershipState}
            for member in self.members.values():
                counts[member.state.value] += 1
            return counts

    def _protocol_loop(self):
        """Main SWIM protocol loop"""
        while self.running:
            try:
                # Select random alive member to ping
                alive_members = []
                with self.lock:
                    alive_members = [
                        member
                        for member in self.members.values()
                        if member.is_alive
                        and member.node_info.node_id != self.node_info.node_id
                    ]

                if alive_members:
                    target = random.choice(alive_members)
                    self._ping_member(target)

                # Check for suspect timeouts
                self._check_suspect_timeouts()

                # Clean up old gossip updates
                self._cleanup_gossip_updates()

                time.sleep(self.protocol_interval)

            except Exception as e:
                self.logger.error(f"Error in protocol loop: {e}")

    def _ping_member(self, member: SwimMember):
        """Send ping to a member"""
        ping_msg = SwimMessage(
            type=MessageType.PING,
            sender_id=self.node_info.node_id,
            target_id=member.node_info.node_id,
            incarnation=self.incarnation,
            piggyback_updates=self._get_piggyback_updates(),
        )

        self._send_message(ping_msg, member.node_info.ip_address, self.port)

        # Set up timeout to mark as suspect if no ACK received
        def timeout_handler():
            time.sleep(self.suspect_timeout)
            with self.lock:
                if (
                    member.node_info.node_id in self.members
                    and self.members[member.node_info.node_id].is_alive
                ):
                    self._mark_suspect(member.node_info.node_id)

        threading.Thread(target=timeout_handler, daemon=True).start()

    def _mark_suspect(self, node_id: str):
        """Mark a node as suspect"""
        with self.lock:
            if node_id in self.members:
                member = self.members[node_id]
                if member.is_alive:  # Only transition from alive to suspect
                    member.state = MembershipState.SUSPECT
                    member.suspect_timeout = time.time() + self.failure_timeout
                    member.last_update = time.time()

                    # Create and gossip suspect update
                    update = MembershipUpdate(
                        node_id=node_id,
                        state=MembershipState.SUSPECT,
                        incarnation=member.incarnation,
                        timestamp=time.time(),
                        source_node=self.node_info.node_id,
                    )

                    self._add_gossip_update(update)
                    self.logger.warning(f"Marked node {node_id} as SUSPECT")

    def _check_suspect_timeouts(self):
        """Check for suspect nodes that should be marked as failed"""
        current_time = time.time()
        failed_nodes = []

        with self.lock:
            for node_id, member in self.members.items():
                if (
                    member.is_suspect
                    and member.suspect_timeout
                    and current_time > member.suspect_timeout
                ):
                    member.state = MembershipState.FAILED
                    member.last_update = current_time
                    failed_nodes.append(member.node_info)

                    # Create and gossip failure update
                    update = MembershipUpdate(
                        node_id=node_id,
                        state=MembershipState.FAILED,
                        incarnation=member.incarnation,
                        timestamp=current_time,
                        source_node=self.node_info.node_id,
                    )

                    self._add_gossip_update(update)
                    self.logger.error(f"Node {node_id} marked as FAILED")

        # Notify callbacks
        for node_info in failed_nodes:
            if self.member_failed_callback:
                try:
                    self.member_failed_callback(node_info)
                except Exception as e:
                    self.logger.error(f"Error in member failed callback: {e}")

    def _message_listener(self):
        """Listen for SWIM protocol messages"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65536)
                message_data = json.loads(data.decode("utf-8"))
                message = SwimMessage(**message_data)

                self._handle_message(message, addr[0])

            except Exception as e:
                if self.running:  # Only log if we're still running
                    self.logger.error(f"Error in message listener: {e}")

    def _handle_message(self, message: SwimMessage, sender_ip: str):
        """Handle incoming SWIM protocol message"""
        try:
            # Process piggyback updates first
            if message.piggyback_updates:
                for update_data in message.piggyback_updates:
                    if isinstance(update_data, dict):
                        update = MembershipUpdate(**update_data)
                        self._process_membership_update(update)

            # Handle specific message types
            if message.type == MessageType.PING:
                self._handle_ping(message, sender_ip)
            elif message.type == MessageType.ACK:
                self._handle_ack(message)
            elif message.type == MessageType.JOIN:
                self._handle_join(message, sender_ip)
            elif message.type == MessageType.SYNC:
                self._handle_dns_sync(message)

        except Exception as e:
            self.logger.error(f"Error handling message from {sender_ip}: {e}")

    def _handle_ping(self, message: SwimMessage, sender_ip: str):
        """Handle ping message"""
        # Send ACK back
        ack_msg = SwimMessage(
            type=MessageType.ACK,
            sender_id=self.node_info.node_id,
            target_id=message.sender_id,
            incarnation=self.incarnation,
            piggyback_updates=self._get_piggyback_updates(),
        )

        self._send_message(ack_msg, sender_ip, self.port)

    def _handle_ack(self, message: SwimMessage):
        """Handle ACK message"""
        # ACK received, node is alive
        with self.lock:
            if message.sender_id in self.members:
                member = self.members[message.sender_id]
                if member.is_suspect:
                    # Node responded, mark as alive
                    member.state = MembershipState.ALIVE
                    member.suspect_timeout = None
                    member.last_update = time.time()

                    # Create and gossip alive update
                    update = MembershipUpdate(
                        node_id=message.sender_id,
                        state=MembershipState.ALIVE,
                        incarnation=message.incarnation,
                        timestamp=time.time(),
                        source_node=self.node_info.node_id,
                    )

                    self._add_gossip_update(update)
                    self.logger.info(f"Node {message.sender_id} confirmed ALIVE")

    def _handle_join(self, message: SwimMessage, sender_ip: str):
        """Handle join request"""
        if message.payload and "node_info" in message.payload:
            node_info = NodeInfo(**message.payload["node_info"])

            with self.lock:
                if node_info.node_id not in self.members:
                    # Add new member
                    self.members[node_info.node_id] = SwimMember(
                        node_info=node_info,
                        state=MembershipState.ALIVE,
                        incarnation=message.incarnation,
                        last_update=time.time(),
                    )

                    # Create and gossip join update
                    update = MembershipUpdate(
                        node_id=node_info.node_id,
                        state=MembershipState.ALIVE,
                        incarnation=message.incarnation,
                        timestamp=time.time(),
                        source_node=self.node_info.node_id,
                    )

                    self._add_gossip_update(update)
                    self.logger.info(f"Node {node_info.node_id} joined cluster")

                    # Notify callback
                    if self.member_joined_callback:
                        try:
                            self.member_joined_callback(node_info)
                        except Exception as e:
                            self.logger.error(f"Error in member joined callback: {e}")

            # Send current membership state back
            self._send_membership_sync(sender_ip)

    def _handle_dns_sync(self, message: SwimMessage):
        """Handle DNS record synchronization"""
        if message.payload and "dns_records" in message.payload:
            remote_records = message.payload["dns_records"]
            remote_version = message.payload.get("version", 0)

            # Simple conflict resolution: higher version wins
            if remote_version > self.dns_version:
                with self.lock:
                    self.dns_records.update(remote_records)
                    self.dns_version = remote_version

                if self.dns_sync_callback:
                    try:
                        self.dns_sync_callback(remote_records)
                    except Exception as e:
                        self.logger.error(f"Error in DNS sync callback: {e}")

                self.logger.info(f"Synchronized DNS records (version {remote_version})")

    def _process_membership_update(self, update: MembershipUpdate):
        """Process a membership update from gossip"""
        with self.lock:
            if update.node_id in self.members:
                member = self.members[update.node_id]

                # Apply update if it's newer (higher incarnation)
                if update.incarnation >= member.incarnation:
                    member.state = update.state
                    member.incarnation = update.incarnation
                    member.last_update = update.timestamp

                    # Continue gossiping this update
                    self._add_gossip_update(update)

    def _add_gossip_update(self, update: MembershipUpdate):
        """Add update to gossip queue"""
        with self.lock:
            self.pending_updates.append(update)
            update_key = f"{update.node_id}:{update.state.value}:{update.incarnation}"
            self.update_counts[update_key] = 0

    def _get_piggyback_updates(self) -> List[Dict[str, Any]]:
        """Get updates to piggyback on messages"""
        with self.lock:
            # Return serializable updates
            updates = []
            for update in self.pending_updates[: self.max_piggyback]:
                updates.append(asdict(update))
            return updates

    def _cleanup_gossip_updates(self):
        """Clean up old gossip updates that have been spread enough"""
        with self.lock:
            # Remove updates that have been gossiped enough times
            self.pending_updates = [
                update
                for update in self.pending_updates
                if self.update_counts.get(
                    f"{update.node_id}:{update.state.value}:{update.incarnation}", 0
                )
                < self.gossip_factor * 2
            ]

    def _gossip_dns_sync(self):
        """Gossip DNS record synchronization"""
        alive_nodes = []
        with self.lock:
            alive_nodes = [
                member
                for member in self.members.values()
                if member.is_alive
                and member.node_info.node_id != self.node_info.node_id
            ]

        if not alive_nodes:
            return

        # Select random nodes to sync with
        targets = random.sample(alive_nodes, min(self.gossip_factor, len(alive_nodes)))

        sync_msg = SwimMessage(
            type=MessageType.SYNC,
            sender_id=self.node_info.node_id,
            payload={
                "dns_records": self.dns_records.copy(),
                "version": self.dns_version,
            },
        )

        for target in targets:
            self._send_message(sync_msg, target.node_info.ip_address, self.port)

    def _send_membership_sync(self, target_ip: str):
        """Send current membership state to a node"""
        with self.lock:
            membership_data = {}
            for node_id, member in self.members.items():
                membership_data[node_id] = {
                    "node_info": asdict(member.node_info),
                    "state": member.state.value,
                    "incarnation": member.incarnation,
                }

        sync_msg = SwimMessage(
            type=MessageType.SYNC,
            sender_id=self.node_info.node_id,
            payload={"membership": membership_data},
        )

        self._send_message(sync_msg, target_ip, self.port)

    def _broadcast_leave(self):
        """Broadcast leave message to all alive members"""
        alive_nodes = []
        with self.lock:
            alive_nodes = [
                member
                for member in self.members.values()
                if member.is_alive
                and member.node_info.node_id != self.node_info.node_id
            ]

        leave_msg = SwimMessage(
            type=MessageType.LEAVE,
            sender_id=self.node_info.node_id,
            incarnation=self.incarnation,
        )

        for member in alive_nodes:
            try:
                self._send_message(leave_msg, member.node_info.ip_address, self.port)
            except Exception as e:
                self.logger.error(
                    f"Failed to send leave to {member.node_info.node_id}: {e}"
                )

    def _send_message(self, message: SwimMessage, target_ip: str, target_port: int):
        """Send a SWIM message to a target"""
        try:
            # Convert message to dict for JSON serialization
            message_dict = asdict(message)
            data = json.dumps(message_dict).encode("utf-8")

            self.socket.sendto(data, (target_ip, target_port))

        except Exception as e:
            self.logger.error(
                f"Failed to send message to {target_ip}:{target_port}: {e}"
            )


def create_swim_node(
    node_info: NodeInfo, swim_port: int = 8888, **kwargs
) -> SwimProtocol:
    """
    Create a SWIM protocol node

    Args:
        node_info: Node information
        swim_port: Port for SWIM protocol communication
        **kwargs: Additional SwimProtocol parameters

    Returns:
        Configured SwimProtocol instance
    """
    return SwimProtocol(node_info=node_info, port=swim_port, **kwargs)
