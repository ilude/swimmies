"""Tests for swimmies gossip protocol functionality."""

import time

from swimmies.gossip import GossipMessage, GossipNode


def test_gossip_message_creation():
    """Test GossipMessage creation."""
    message = GossipMessage(
        sender_id="node1",
        message_type="hello",
        payload={"test": "data"},
        timestamp=time.time()
    )
    assert message.sender_id == "node1"
    assert message.message_type == "hello"
    assert message.payload["test"] == "data"


def test_gossip_node_creation():
    """Test GossipNode creation and basic operations."""
    node = GossipNode("test_node")
    assert node.node_id == "test_node"
    assert len(node.peers) == 0
    
    node.add_peer("peer1")
    assert "peer1" in node.peers
    assert len(node.peers) == 1


def test_gossip_node_messaging(capfd):
    """Test gossip node message sending and receiving."""
    node = GossipNode("test_node")
    message = GossipMessage(
        sender_id="sender",
        message_type="test",
        payload={},
        timestamp=time.time()
    )
    
    node.send_message(message)
    captured = capfd.readouterr()
    assert "test_node sending message" in captured.out
    
    node.receive_message(message)
    captured = capfd.readouterr()
    assert "test_node received message from sender" in captured.out
