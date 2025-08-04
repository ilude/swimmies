"""
Node discovery module for LAN/subnet broadcasts.

Provides UDP broadcast functionality for automatic discovery of joyride nodes
on the same subnet with basic node registration and heartbeat mechanism.
"""

import json
import logging
import socket
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """Information about a discovered node."""

    node_id: str
    hostname: str
    ip_address: str
    port: int
    service_type: str
    last_seen: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["last_seen"] = self.last_seen.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeInfo":
        """Create NodeInfo from dictionary."""
        data["last_seen"] = datetime.fromisoformat(data["last_seen"])
        return cls(**data)


@dataclass
class DiscoveryMessage:
    """Message format for node discovery broadcasts."""

    message_type: str  # 'announce', 'heartbeat', 'goodbye'
    node_info: NodeInfo
    timestamp: datetime

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {
            "message_type": self.message_type,
            "node_info": self.node_info.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DiscoveryMessage":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["node_info"] = NodeInfo.from_dict(data["node_info"])
        return cls(**data)


class NodeDiscovery:
    """UDP broadcast-based node discovery service."""

    def __init__(
        self,
        node_id: str,
        service_type: str = "joyride-dns",
        broadcast_port: int = 8889,
        heartbeat_interval: int = 30,
        node_timeout: int = 90,
        bind_address: str = "0.0.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize node discovery service.

        Args:
            node_id: Unique identifier for this node
            service_type: Type of service for filtering
            broadcast_port: UDP port for broadcasts
            heartbeat_interval: Seconds between heartbeat broadcasts
            node_timeout: Seconds before considering a node dead
            bind_address: Address to bind to for receiving broadcasts
            metadata: Additional node metadata
        """
        self.node_id = node_id
        self.service_type = service_type
        self.broadcast_port = broadcast_port
        self.heartbeat_interval = heartbeat_interval
        self.node_timeout = node_timeout
        self.bind_address = bind_address
        self.metadata = metadata or {}

        self.local_node = NodeInfo(
            node_id=node_id,
            hostname=socket.gethostname(),
            ip_address=self._get_local_ip(),
            port=broadcast_port,
            service_type=service_type,
            last_seen=datetime.now(),
            metadata=self.metadata,
        )

        self.discovered_nodes: Dict[str, NodeInfo] = {}
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.broadcast_thread: Optional[threading.Thread] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None

        # Callback for node events
        self.on_node_discovered: Optional[Callable[[NodeInfo], None]] = None
        self.on_node_lost: Optional[Callable[[NodeInfo], None]] = None
        self.on_node_updated: Optional[Callable[[NodeInfo], None]] = None

    def _get_local_ip(self) -> str:
        """Get the local IP address."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _setup_socket(self) -> socket.socket:
        """Setup UDP socket for broadcasting and receiving."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((self.bind_address, self.broadcast_port))
        return sock

    def start(self) -> None:
        """Start the discovery service."""
        if self.running:
            return

        logger.info(f"Starting node discovery for {self.node_id}")
        self.running = True

        try:
            self.sock = self._setup_socket()

            # Start listener thread
            self.listener_thread = threading.Thread(target=self._listen_loop)
            self.listener_thread.daemon = True
            self.listener_thread.start()

            # Start broadcast thread
            self.broadcast_thread = threading.Thread(target=self._broadcast_loop)
            self.broadcast_thread.daemon = True
            self.broadcast_thread.start()

            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
            self.cleanup_thread.daemon = True
            self.cleanup_thread.start()

            # Send initial announcement
            self._broadcast_message("announce")

        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}")
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the discovery service."""
        if not self.running:
            return

        logger.info(f"Stopping node discovery for {self.node_id}")
        self.running = False

        # Send goodbye message
        try:
            if self.sock:
                self._broadcast_message("goodbye")
        except Exception as e:
            logger.warning(f"Error sending goodbye message: {e}")

        # Close socket
        if self.sock:
            self.sock.close()
            self.sock = None

        # Wait for threads to finish
        for thread in [
            self.listener_thread,
            self.broadcast_thread,
            self.cleanup_thread,
        ]:
            if thread and thread.is_alive():
                thread.join(timeout=1.0)

    def _broadcast_message(self, message_type: str) -> None:
        """Broadcast a discovery message."""
        if not self.sock or not self.running:
            return

        self.local_node.last_seen = datetime.now()
        message = DiscoveryMessage(
            message_type=message_type,
            node_info=self.local_node,
            timestamp=datetime.now(),
        )

        try:
            data = message.to_json().encode("utf-8")
            self.sock.sendto(data, ("<broadcast>", self.broadcast_port))
            logger.debug(f"Broadcast {message_type} message from {self.node_id}")
        except Exception as e:
            logger.error(f"Error broadcasting {message_type} message: {e}")

    def _broadcast_loop(self) -> None:
        """Main broadcast loop for heartbeat messages."""
        while self.running:
            time.sleep(self.heartbeat_interval)
            if self.running:
                self._broadcast_message("heartbeat")

    def _listen_loop(self) -> None:
        """Main listening loop for incoming discovery messages."""
        if not self.sock:
            return

        self.sock.settimeout(1.0)  # Allow periodic checks of running flag

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self._handle_message(data.decode("utf-8"), addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving discovery message: {e}")

    def _handle_message(self, data: str, addr: tuple) -> None:
        """Handle incoming discovery message."""
        try:
            message = DiscoveryMessage.from_json(data)

            # Ignore messages from ourselves
            if message.node_info.node_id == self.node_id:
                return

            # Filter by service type
            if message.node_info.service_type != self.service_type:
                return

            node_id = message.node_info.node_id

            if message.message_type == "goodbye":
                self._remove_node(node_id)
            else:
                self._update_node(message.node_info)

        except Exception as e:
            logger.warning(f"Error parsing discovery message from {addr}: {e}")

    def _update_node(self, node_info: NodeInfo) -> None:
        """Update information about a discovered node."""
        node_id = node_info.node_id
        is_new_node = node_id not in self.discovered_nodes

        self.discovered_nodes[node_id] = node_info

        if is_new_node:
            logger.info(f"Discovered new node: {node_id} at {node_info.ip_address}")
            if self.on_node_discovered:
                self.on_node_discovered(node_info)
        else:
            logger.debug(f"Updated node: {node_id}")
            if self.on_node_updated:
                self.on_node_updated(node_info)

    def _remove_node(self, node_id: str) -> None:
        """Remove a node from discovered nodes."""
        if node_id in self.discovered_nodes:
            node_info = self.discovered_nodes.pop(node_id)
            logger.info(f"Node left: {node_id}")
            if self.on_node_lost:
                self.on_node_lost(node_info)

    def _cleanup_loop(self) -> None:
        """Clean up expired nodes."""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            if not self.running:
                break

            now = datetime.now()
            expired_nodes = []

            for node_id, node_info in self.discovered_nodes.items():
                if now - node_info.last_seen > timedelta(seconds=self.node_timeout):
                    expired_nodes.append(node_id)

            for node_id in expired_nodes:
                self._remove_node(node_id)

    def get_discovered_nodes(self) -> List[NodeInfo]:
        """Get list of currently discovered nodes."""
        return list(self.discovered_nodes.values())

    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """Get information about a specific node."""
        return self.discovered_nodes.get(node_id)

    def is_running(self) -> bool:
        """Check if discovery service is running."""
        return self.running
