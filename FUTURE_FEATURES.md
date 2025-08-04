# Swimmies Library - Future Features & Roadmap

## Current Goal: LAN/Subnet Node Discovery
- Implement UDP broadcast functionality for local network node discovery
- Support automatic discovery of joyride nodes on same subnet
- Basic node registration and heartbeat mechanism

## Phase 1: SWIM/Gossip Protocol Foundation
- Add SWIM (Scalable Weakly-consistent Infection-style Process Group Membership) protocol
- Implement gossip-based communication for distributed systems
- Node failure detection and recovery mechanisms
- Distributed DNS record synchronization between joyride nodes

## Phase 2: Cross-Subnet Discovery
- Support for manual node IP address configuration
- FQDN-based node discovery across network boundaries
- NAT traversal and firewall considerations
- Secure inter-node communication

## Phase 3: Advanced Features
- Encryption for inter-node communication
- Node authentication and authorization
- Conflict resolution for DNS records
- Performance optimization for large node clusters
- Health monitoring and metrics collection

## Integration with Joyride DNS
- Automatic DNS record distribution across discovered nodes
- Failover and load balancing capabilities
- Consistent DNS responses across all nodes
- Integration with Docker container discovery

## Technical Considerations
- UDP multicast for efficient broadcast communication
- Configurable discovery intervals and timeouts
- Support for multiple network interfaces
- IPv4/IPv6 dual-stack support
- Minimal dependencies for easy