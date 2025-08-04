# Swimmies Discovery Demo

This Docker-based demo showcases the UDP broadcast node discovery functionality of the swimmies library. It creates three containerized nodes that automatically discover each other on the same Docker network.

## Quick Start

```bash
# Change to swimmies directory first
cd /workspaces/joyride/swimmies

# Start the demo (builds images and starts 3 nodes)
make demo-start

# Watch the discovery in action
make demo-logs

# Check container status
make demo-status

# Stop the demo
make demo-stop

# Clean up everything
make demo-clean
```

## Demo Architecture

The demo creates three distinct nodes on a shared Docker network:

### 🟦 Node 1 - Primary DNS Server
- **Container**: `swimmies-node-1`
- **Role**: `primary-dns`
- **Port**: `8889:8889/udp`
- **Description**: Acts as the primary DNS server

### 🟨 Node 2 - Secondary DNS Server  
- **Container**: `swimmies-node-2`
- **Role**: `secondary-dns`
- **Port**: `8890:8889/udp`
- **Description**: Provides DNS redundancy

### 🟩 Node 3 - DNS Cache Server
- **Container**: `swimmies-node-3`
- **Role**: `cache-server`
- **Port**: `8891:8889/udp`
- **Description**: Handles DNS caching

## Network Configuration

- **Network**: `discovery-net` (bridge)
- **Subnet**: `172.20.0.0/16`
- **Protocol**: UDP broadcast on port 8889
- **Discovery**: Automatic via UDP broadcasts every 10 seconds
- **Timeout**: Nodes considered lost after 30 seconds

## What You'll See

When you run `make demo-logs`, you'll observe:

1. **Initial Startup**: Each node starts and announces itself
2. **Discovery Events**: Nodes discovering each other with `📡 DISCOVERED` messages
3. **Status Reports**: Every 30 seconds, each node reports discovered peers
4. **Heartbeats**: Continuous UDP broadcasts maintaining node presence
5. **Clean Shutdown**: Graceful goodbye messages when stopping

### Sample Log Output

```
📡 DISCOVERED: discovery-node-2
   Name: Secondary DNS Server
   IP: 172.20.0.3
   Container: node-2
   Role: secondary-dns

📊 STATUS REPORT - 14:23:45
   Node: discovery-node-1 (Primary DNS Server)
   Discovered: 2 other nodes
   Network members:
     - discovery-node-2 (Secondary DNS Server) at 172.20.0.3 (last seen 5s ago)
     - discovery-node-3 (DNS Cache Server) at 172.20.0.4 (last seen 8s ago)
```

## Available Commands

**Note**: All commands must be run from the swimmies directory: `cd /workspaces/joyride/swimmies`

### Make Targets
```bash
make demo-start     # Start all 3 nodes
make demo-stop      # Stop all nodes (containers remain)
make demo-restart   # Restart all nodes
make demo-logs      # Watch logs from all nodes
make demo-logs-1    # Node 1 logs only
make demo-logs-2    # Node 2 logs only  
make demo-logs-3    # Node 3 logs only
make demo-status    # Show container and network status
make demo-clean     # Remove all containers and networks
make demo-build     # Rebuild Docker images
```

All demo functionality is now integrated into the Makefile for a unified development experience.

## Customization

### Environment Variables

You can modify the behavior by editing `docker-compose.yml`:

- `NODE_ID`: Unique identifier for the node
- `NODE_NAME`: Human-readable name
- `SERVICE_TYPE`: Service filter (must match for discovery)
- `BROADCAST_PORT`: UDP port for discovery (default: 8889)
- `HEARTBEAT_INTERVAL`: Seconds between heartbeats (default: 10)
- `NODE_TIMEOUT`: Seconds before considering node lost (default: 30)
- `NODE_ROLE`: Role metadata for the node
- `ENVIRONMENT`: Environment tag

### Adding More Nodes

To add a fourth node, copy the `discovery-node-3` service in `docker-compose.yml` and:

1. Change the service name to `discovery-node-4`
2. Update `container_name` and `hostname`
3. Set unique `NODE_ID` and `NODE_NAME`
4. Choose a different external UDP port (e.g., `8892:8889/udp`)
5. Update the `depends_on` section

## Network Testing

### Internal Network Testing
```bash
# Execute commands inside a running container
docker exec -it swimmies-node-1 /bin/sh

# Test UDP connectivity from within container
nmap -sU -p 8889 172.20.0.0/16
```

### External Monitoring
```bash
# Monitor UDP traffic on host
sudo tcpdump -i docker0 -p udp port 8889

# Check port bindings
netstat -ulnp | grep 8889
```

## Troubleshooting

### Containers Won't Start
```bash
# Change to swimmies directory first
cd /workspaces/joyride/swimmies

# Check Docker daemon
docker info

# Rebuild images
make demo-build

# Check for port conflicts
netstat -ulnp | grep 8889
```

### No Discovery Happening
```bash
# Change to swimmies directory first
cd /workspaces/joyride/swimmies

# Verify network connectivity
docker network inspect swimmies_discovery-net

# Check container logs
make demo-logs

# Verify UDP broadcasts are working
docker exec swimmies-node-1 netstat -ul
```

### Performance Issues
```bash
# Check container resource usage
docker stats

# Monitor network traffic
docker exec swimmies-node-1 iftop
```

## Use Cases

This demo is perfect for:

- **Understanding UDP broadcast discovery**
- **Testing network partitions and recovery**
- **Demonstrating distributed system concepts**
- **Validating discovery timing and reliability**
- **Educational purposes and presentations**
- **Integration testing of the swimmies library**

## Clean Up

Always clean up after testing:

```bash
# Change to swimmies directory first
cd /workspaces/joyride/swimmies

# Full cleanup (recommended)
make demo-clean

# Or manual cleanup
docker compose down --volumes --remove-orphans
docker system prune -f
```

This removes all containers, networks, volumes, and unused images created by the demo.
