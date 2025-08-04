#!/usr/bin/env python3
"""
Multi-node discovery example for Docker demo.

This example is designed to run in Docker containers and demonstrate
node discovery across multiple instances on the same network.
"""

import os
import sys
import time

from swimmies.discovery import NodeDiscovery


def main():
    """Run multi-node discovery example."""
    # Get configuration from environment variables
    node_id = os.getenv("NODE_ID", f"node-{os.getpid()}")
    node_name = os.getenv("NODE_NAME", node_id)
    service_type = os.getenv("SERVICE_TYPE", "joyride-dns")
    broadcast_port = int(os.getenv("BROADCAST_PORT", "8889"))
    heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
    node_timeout = int(os.getenv("NODE_TIMEOUT", "30"))
    
    # Additional metadata
    metadata = {
        "node_name": node_name,
        "version": "1.0.0",
        "container_id": os.getenv("HOSTNAME", "unknown"),
        "role": os.getenv("NODE_ROLE", "dns-server"),
        "environment": os.getenv("ENVIRONMENT", "demo")
    }

    print(f"🚀 Starting discovery node: {node_id}")
    print(f"   Node name: {node_name}")
    print(f"   Service type: {service_type}")
    print(f"   Broadcast port: {broadcast_port}")
    print(f"   Heartbeat interval: {heartbeat_interval}s")
    print(f"   Node timeout: {node_timeout}s")
    print(f"   Container: {metadata['container_id']}")
    print()

    # Create discovery service
    discovery = NodeDiscovery(
        node_id=node_id,
        service_type=service_type,
        broadcast_port=broadcast_port,
        heartbeat_interval=heartbeat_interval,
        node_timeout=node_timeout,
        metadata=metadata
    )

    # Set up event callbacks
    def on_node_discovered(node_info):
        print(f"📡 DISCOVERED: {node_info.node_id}")
        print(f"   Name: {node_info.metadata.get('node_name', 'N/A')}")
        print(f"   IP: {node_info.ip_address}")
        print(f"   Container: {node_info.metadata.get('container_id', 'N/A')}")
        print(f"   Role: {node_info.metadata.get('role', 'N/A')}")
        print()

    def on_node_lost(node_info):
        print(f"💔 LOST: {node_info.node_id} ({node_info.metadata.get('node_name', 'N/A')})")
        print()

    def on_node_updated(node_info):
        print(f"🔄 UPDATED: {node_info.node_id} ({node_info.metadata.get('node_name', 'N/A')})")

    discovery.on_node_discovered = on_node_discovered
    discovery.on_node_lost = on_node_lost
    discovery.on_node_updated = on_node_updated

    try:
        # Start discovery
        discovery.start()
        print(f"✅ Discovery service started for {node_id}")
        print(f"   Local IP: {discovery.local_node.ip_address}")
        print(f"   Listening on port: {broadcast_port}")
        print()
        print("Waiting for other nodes to join the network...")
        print("=" * 50)
        print()

        # Status reporting loop
        last_report = 0
        while True:
            time.sleep(5)
            
            # Report status every 30 seconds
            current_time = time.time()
            if current_time - last_report >= 30:
                nodes = discovery.get_discovered_nodes()
                print(f"📊 STATUS REPORT - {time.strftime('%H:%M:%S')}")
                print(f"   Node: {node_id} ({node_name})")
                print(f"   Discovered: {len(nodes)} other nodes")
                
                if nodes:
                    print("   Network members:")
                    for node in sorted(nodes, key=lambda x: x.node_id):
                        age = time.time() - node.last_seen.timestamp()
                        print(f"     - {node.node_id} ({node.metadata.get('node_name', 'N/A')}) "
                              f"at {node.ip_address} (last seen {age:.0f}s ago)")
                else:
                    print("   No other nodes discovered yet")
                
                print("=" * 50)
                print()
                last_report = current_time

    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down {node_id}...")
    except Exception as e:
        print(f"❌ Error in {node_id}: {e}")
        sys.exit(1)
    finally:
        discovery.stop()
        print(f"✅ Node {node_id} stopped cleanly")


if __name__ == "__main__":
    main()
