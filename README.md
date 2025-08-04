# Swimmies

A utility library for Joyride DNS Service providing common utilities and data structures used across the Joyride DNS ecosystem.

## Features

- **Core Utilities**: DNS record parsing, domain validation
- **Node Discovery**: UDP broadcast-based automatic discovery of nodes on LAN/subnet
- **Gossip Protocol**: Distributed communication primitives for future multi-node support
- **Type Safe**: Full type hints and comprehensive test coverage

## Installation

```bash
pip install swimmies
```

For development:

```bash
git clone <repository-url>
cd swimmies
uv sync --extra dev
```

## Usage

### Node Discovery

Automatic discovery of joyride nodes on the local network using UDP broadcasts:

```python
from swimmies.discovery import NodeDiscovery

# Create discovery service
discovery = NodeDiscovery(
    node_id="my-joyride-node",
    service_type="joyride-dns",
    broadcast_port=8889,
    heartbeat_interval=30,
    metadata={"version": "1.0.0"}
)

# Set up callbacks
def on_node_discovered(node_info):
    print(f"Found node: {node_info.node_id} at {node_info.ip_address}")

discovery.on_node_discovered = on_node_discovered

# Start discovery
discovery.start()

# Get discovered nodes
nodes = discovery.get_discovered_nodes()
for node in nodes:
    print(f"Node: {node.node_id} at {node.ip_address}")

# Stop when done
discovery.stop()
```

### Core Utilities

```python
import swimmies
from swimmies import GossipNode, GossipMessage

# Core utilities
swimmies.hello_world()

# Gossip protocol (future feature)
node = GossipNode("my-node")
node.add_peer("peer-1")
```

## Architecture

### Node Discovery Protocol

The discovery system uses UDP broadcasts for automatic node discovery:

- **Broadcast Messages**: Nodes periodically broadcast their presence
- **Service Filtering**: Only nodes with matching service types are discovered
- **Heartbeat System**: Regular heartbeats maintain node liveness
- **Timeout Handling**: Nodes that stop responding are automatically removed
- **Callbacks**: Event-driven notifications for node discovery/loss/updates

### Message Format

Discovery messages are JSON-encoded with the following structure:

```json
{
  "message_type": "announce|heartbeat|goodbye",
  "node_info": {
    "node_id": "unique-node-identifier",
    "hostname": "node-hostname",
    "ip_address": "192.168.1.100",
    "port": 8889,
    "service_type": "joyride-dns",
    "last_seen": "2025-08-04T12:00:00",
    "metadata": {"version": "1.0.0"}
  },
  "timestamp": "2025-08-04T12:00:00"
}
```

## Development

This library is designed to work with UV workspaces and follows modern Python packaging practices.

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=swimmies --cov-report=html

# Run specific test module
uv run pytest tests/test_discovery.py -v
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint code
uv run flake8 src/ tests/
```

### Building

```bash
uv build
```

## License

MIT License - see LICENSE file for details.
