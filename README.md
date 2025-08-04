# Swimmies

A utility library for Joyride DNS Service providing common utilities and data structures used across the Joyride DNS ecosystem.

## Features

- **Core Utilities**: DNS record parsing, domain validation
- **Gossip Protocol**: Distributed communication primitives for future multi-node support
- **Type Safe**: Full type hints and Pydantic integration ready

## Installation

```bash
pip install swimmies
```

For development:

```bash
git clone <repository-url>
cd swimmies
uv sync
```

## Usage

```python
import swimmies
from swimmies import GossipNode, GossipMessage

# Core utilities
swimmies.hello_world()

# Gossip protocol
node = GossipNode("my-node")
node.add_peer("peer-1")
```

## Development

This library is designed to work with UV workspaces and follows modern Python packaging practices.

### Testing

```bash
uv run pytest tests/ -v
```

### Building

```bash
uv build
```

## License

MIT License - see LICENSE file for details.
