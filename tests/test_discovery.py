"""
Tests for the node discovery module.
"""

import json
import socket
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from swimmies.discovery import DiscoveryMessage, NodeDiscovery, NodeInfo


class TestNodeInfo:
    """Tests for NodeInfo class."""

    def test_node_info_creation(self):
        """Test NodeInfo creation and basic properties."""
        now = datetime.now()
        node = NodeInfo(
            node_id="test-node",
            hostname="testhost",
            ip_address="192.168.1.100",
            port=8889,
            service_type="joyride-dns",
            last_seen=now,
            metadata={"version": "1.0"},
        )

        assert node.node_id == "test-node"
        assert node.hostname == "testhost"
        assert node.ip_address == "192.168.1.100"
        assert node.port == 8889
        assert node.service_type == "joyride-dns"
        assert node.last_seen == now
        assert node.metadata == {"version": "1.0"}

    def test_node_info_serialization(self):
        """Test NodeInfo to_dict and from_dict methods."""
        now = datetime.now()
        node = NodeInfo(
            node_id="test-node",
            hostname="testhost",
            ip_address="192.168.1.100",
            port=8889,
            service_type="joyride-dns",
            last_seen=now,
            metadata={"version": "1.0"},
        )

        # Test serialization
        data = node.to_dict()
        assert data["node_id"] == "test-node"
        assert data["last_seen"] == now.isoformat()

        # Test deserialization
        restored_node = NodeInfo.from_dict(data)
        assert restored_node.node_id == node.node_id
        assert restored_node.hostname == node.hostname
        assert restored_node.ip_address == node.ip_address
        assert restored_node.port == node.port
        assert restored_node.service_type == node.service_type
        assert restored_node.last_seen == node.last_seen
        assert restored_node.metadata == node.metadata


class TestDiscoveryMessage:
    """Tests for DiscoveryMessage class."""

    def test_discovery_message_creation(self):
        """Test DiscoveryMessage creation."""
        now = datetime.now()
        node = NodeInfo(
            node_id="test-node",
            hostname="testhost",
            ip_address="192.168.1.100",
            port=8889,
            service_type="joyride-dns",
            last_seen=now,
            metadata={},
        )

        message = DiscoveryMessage(
            message_type="announce", node_info=node, timestamp=now
        )

        assert message.message_type == "announce"
        assert message.node_info == node
        assert message.timestamp == now

    def test_discovery_message_json_serialization(self):
        """Test DiscoveryMessage JSON serialization."""
        now = datetime.now()
        node = NodeInfo(
            node_id="test-node",
            hostname="testhost",
            ip_address="192.168.1.100",
            port=8889,
            service_type="joyride-dns",
            last_seen=now,
            metadata={"version": "1.0"},
        )

        message = DiscoveryMessage(
            message_type="announce", node_info=node, timestamp=now
        )

        # Test serialization
        json_str = message.to_json()
        assert isinstance(json_str, str)

        # Verify JSON structure
        data = json.loads(json_str)
        assert data["message_type"] == "announce"
        assert "node_info" in data
        assert "timestamp" in data

        # Test deserialization
        restored_message = DiscoveryMessage.from_json(json_str)
        assert restored_message.message_type == message.message_type
        assert restored_message.node_info.node_id == message.node_info.node_id
        assert restored_message.timestamp == message.timestamp


class TestNodeDiscovery:
    """Tests for NodeDiscovery class."""

    @pytest.fixture
    def discovery_service(self):
        """Create a NodeDiscovery instance for testing."""
        return NodeDiscovery(
            node_id="test-node-1",
            service_type="test-service",
            broadcast_port=0,  # Use random port
            heartbeat_interval=1,
            node_timeout=5,
        )

    def test_node_discovery_initialization(self, discovery_service):
        """Test NodeDiscovery initialization."""
        assert discovery_service.node_id == "test-node-1"
        assert discovery_service.service_type == "test-service"
        assert discovery_service.heartbeat_interval == 1
        assert discovery_service.node_timeout == 5
        assert not discovery_service.running
        assert len(discovery_service.discovered_nodes) == 0

    def test_local_node_creation(self, discovery_service):
        """Test that local node info is created correctly."""
        local_node = discovery_service.local_node
        assert local_node.node_id == "test-node-1"
        assert local_node.service_type == "test-service"
        assert local_node.hostname is not None
        assert local_node.ip_address is not None

    @patch("socket.socket")
    def test_socket_setup(self, mock_socket, discovery_service):
        """Test UDP socket setup."""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        discovery_service._setup_socket()

        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        mock_sock.bind.assert_called_once()

    def test_get_local_ip(self, discovery_service):
        """Test local IP detection."""
        ip = discovery_service._get_local_ip()
        assert isinstance(ip, str)
        assert len(ip) > 0
        # Should be valid IP format (basic check)
        parts = ip.split(".")
        assert len(parts) == 4

    @patch("swimmies.discovery.socket.socket")
    def test_start_and_stop(self, mock_socket, discovery_service):
        """Test starting and stopping the discovery service."""
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # Test start
        discovery_service.start()
        assert discovery_service.running
        assert discovery_service.sock is not None

        # Verify threads are started
        assert discovery_service.listener_thread is not None
        assert discovery_service.broadcast_thread is not None
        assert discovery_service.cleanup_thread is not None

        # Test stop
        discovery_service.stop()
        assert not discovery_service.running
        mock_sock.close.assert_called_once()

    def test_message_handling_ignore_self(self, discovery_service):
        """Test that messages from self are ignored."""
        # Create message from same node
        now = datetime.now()
        message = DiscoveryMessage(
            message_type="announce",
            node_info=discovery_service.local_node,
            timestamp=now,
        )

        initial_count = len(discovery_service.discovered_nodes)
        discovery_service._handle_message(message.to_json(), ("127.0.0.1", 8889))

        # Should not add self to discovered nodes
        assert len(discovery_service.discovered_nodes) == initial_count

    def test_message_handling_different_service_type(self, discovery_service):
        """Test that messages from different service types are ignored."""
        now = datetime.now()
        other_node = NodeInfo(
            node_id="other-node",
            hostname="otherhost",
            ip_address="192.168.1.101",
            port=8889,
            service_type="different-service",  # Different service type
            last_seen=now,
            metadata={},
        )

        message = DiscoveryMessage(
            message_type="announce", node_info=other_node, timestamp=now
        )

        initial_count = len(discovery_service.discovered_nodes)
        discovery_service._handle_message(message.to_json(), ("192.168.1.101", 8889))

        # Should not add node with different service type
        assert len(discovery_service.discovered_nodes) == initial_count

    def test_node_discovery_and_update(self, discovery_service):
        """Test discovering and updating nodes."""
        # Mock callbacks
        discovery_service.on_node_discovered = Mock()
        discovery_service.on_node_updated = Mock()

        now = datetime.now()
        other_node = NodeInfo(
            node_id="other-node",
            hostname="otherhost",
            ip_address="192.168.1.101",
            port=8889,
            service_type="test-service",
            last_seen=now,
            metadata={"version": "1.0"},
        )

        # Test discovery
        message = DiscoveryMessage(
            message_type="announce", node_info=other_node, timestamp=now
        )

        discovery_service._handle_message(message.to_json(), ("192.168.1.101", 8889))

        assert len(discovery_service.discovered_nodes) == 1
        assert "other-node" in discovery_service.discovered_nodes
        discovery_service.on_node_discovered.assert_called_once_with(other_node)

        # Test update
        updated_node = NodeInfo(
            node_id="other-node",
            hostname="otherhost",
            ip_address="192.168.1.101",
            port=8889,
            service_type="test-service",
            last_seen=datetime.now(),
            metadata={"version": "1.1"},  # Updated version
        )

        update_message = DiscoveryMessage(
            message_type="heartbeat", node_info=updated_node, timestamp=datetime.now()
        )

        discovery_service._handle_message(
            update_message.to_json(), ("192.168.1.101", 8889)
        )

        assert len(discovery_service.discovered_nodes) == 1
        stored_node = discovery_service.discovered_nodes["other-node"]
        assert stored_node.metadata["version"] == "1.1"
        discovery_service.on_node_updated.assert_called_once()

    def test_node_goodbye_message(self, discovery_service):
        """Test handling goodbye messages."""
        # Mock callback
        discovery_service.on_node_lost = Mock()

        # First add a node
        now = datetime.now()
        other_node = NodeInfo(
            node_id="other-node",
            hostname="otherhost",
            ip_address="192.168.1.101",
            port=8889,
            service_type="test-service",
            last_seen=now,
            metadata={},
        )

        discovery_service.discovered_nodes["other-node"] = other_node

        # Send goodbye message
        goodbye_message = DiscoveryMessage(
            message_type="goodbye", node_info=other_node, timestamp=datetime.now()
        )

        discovery_service._handle_message(
            goodbye_message.to_json(), ("192.168.1.101", 8889)
        )

        assert len(discovery_service.discovered_nodes) == 0
        discovery_service.on_node_lost.assert_called_once_with(other_node)

    def test_node_cleanup_expired(self, discovery_service):
        """Test cleanup of expired nodes."""
        # Mock callback
        discovery_service.on_node_lost = Mock()

        # Add an expired node
        expired_time = datetime.now() - timedelta(
            seconds=discovery_service.node_timeout + 10
        )
        expired_node = NodeInfo(
            node_id="expired-node",
            hostname="expiredhost",
            ip_address="192.168.1.102",
            port=8889,
            service_type="test-service",
            last_seen=expired_time,
            metadata={},
        )

        discovery_service.discovered_nodes["expired-node"] = expired_node

        # Add a current node
        current_node = NodeInfo(
            node_id="current-node",
            hostname="currenthost",
            ip_address="192.168.1.103",
            port=8889,
            service_type="test-service",
            last_seen=datetime.now(),
            metadata={},
        )

        discovery_service.discovered_nodes["current-node"] = current_node

        # Test the cleanup logic directly instead of the loop
        now = datetime.now()
        expired_nodes = []

        for node_id, node_info in discovery_service.discovered_nodes.items():
            if now - node_info.last_seen > timedelta(
                seconds=discovery_service.node_timeout
            ):
                expired_nodes.append(node_id)

        for node_id in expired_nodes:
            discovery_service._remove_node(node_id)

        # Only current node should remain
        assert len(discovery_service.discovered_nodes) == 1
        assert "current-node" in discovery_service.discovered_nodes
        assert "expired-node" not in discovery_service.discovered_nodes
        discovery_service.on_node_lost.assert_called_once_with(expired_node)

    def test_get_discovered_nodes(self, discovery_service):
        """Test getting list of discovered nodes."""
        # Add some nodes
        node1 = NodeInfo(
            node_id="node1",
            hostname="host1",
            ip_address="192.168.1.101",
            port=8889,
            service_type="test-service",
            last_seen=datetime.now(),
            metadata={},
        )

        node2 = NodeInfo(
            node_id="node2",
            hostname="host2",
            ip_address="192.168.1.102",
            port=8889,
            service_type="test-service",
            last_seen=datetime.now(),
            metadata={},
        )

        discovery_service.discovered_nodes["node1"] = node1
        discovery_service.discovered_nodes["node2"] = node2

        nodes = discovery_service.get_discovered_nodes()
        assert len(nodes) == 2
        assert node1 in nodes
        assert node2 in nodes

    def test_get_node(self, discovery_service):
        """Test getting specific node information."""
        node = NodeInfo(
            node_id="test-node",
            hostname="testhost",
            ip_address="192.168.1.101",
            port=8889,
            service_type="test-service",
            last_seen=datetime.now(),
            metadata={},
        )

        discovery_service.discovered_nodes["test-node"] = node

        # Test existing node
        retrieved_node = discovery_service.get_node("test-node")
        assert retrieved_node == node

        # Test non-existing node
        missing_node = discovery_service.get_node("missing-node")
        assert missing_node is None

    def test_invalid_json_handling(self, discovery_service):
        """Test handling of invalid JSON messages."""
        # Should not raise exception
        discovery_service._handle_message("invalid json", ("127.0.0.1", 8889))

        # Should not add any nodes
        assert len(discovery_service.discovered_nodes) == 0


class TestNodeDiscoveryIntegration:
    """Integration tests for NodeDiscovery."""

    def test_two_nodes_discovery(self):
        """Test two nodes discovering each other."""
        # Create two discovery services with different ports
        node1 = NodeDiscovery(
            node_id="node1",
            service_type="test-service",
            broadcast_port=0,  # Random port
            heartbeat_interval=0.5,
            node_timeout=2,
        )

        node2 = NodeDiscovery(
            node_id="node2",
            service_type="test-service",
            broadcast_port=0,  # Random port
            heartbeat_interval=0.5,
            node_timeout=2,
        )

        # Mock callbacks
        node1_discovered = Mock()
        node2_discovered = Mock()
        node1.on_node_discovered = node1_discovered
        node2.on_node_discovered = node2_discovered

        try:
            # For integration test, we'll simulate message exchange
            # rather than actual network communication to avoid port conflicts

            # Simulate node1 announcing to node2
            announce_msg = DiscoveryMessage(
                message_type="announce",
                node_info=node1.local_node,
                timestamp=datetime.now(),
            )

            node2._handle_message(announce_msg.to_json(), ("127.0.0.1", 8889))

            # Verify node2 discovered node1
            assert len(node2.discovered_nodes) == 1
            assert "node1" in node2.discovered_nodes

            # Simulate node2 announcing to node1
            announce_msg2 = DiscoveryMessage(
                message_type="announce",
                node_info=node2.local_node,
                timestamp=datetime.now(),
            )

            node1._handle_message(announce_msg2.to_json(), ("127.0.0.1", 8889))

            # Verify node1 discovered node2
            assert len(node1.discovered_nodes) == 1
            assert "node2" in node1.discovered_nodes

        finally:
            node1.stop()
            node2.stop()
