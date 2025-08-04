#!/usr/bin/env python3
"""
Example usage of the swimmies discovery module.

This example demonstrates how to use the NodeDiscovery class to discover
other nodes on the local network using UDP broadcasts.
"""

import time

from swimmies.discovery import NodeDiscovery


def main():
    """Run discovery example."""
    # Create a discovery service
    discovery = NodeDiscovery(
        node_id="example-node-1",
        service_type="joyride-dns",
        broadcast_port=8889,
        heartbeat_interval=10,
        node_timeout=30,
        metadata={"version": "1.0.0", "role": "dns-server"}
    )

    # Set up callbacks
    def on_node_discovered(node_info):
        print(f"📡 Discovered node: {node_info.node_id} at {node_info.ip_address}")
        print(f"   Hostname: {node_info.hostname}")
        print(f"   Metadata: {node_info.metadata}")

    def on_node_lost(node_info):
        print(f"💔 Lost node: {node_info.node_id}")

    def on_node_updated(node_info):
        print(f"🔄 Updated node: {node_info.node_id}")

    discovery.on_node_discovered = on_node_discovered
    discovery.on_node_lost = on_node_lost
    discovery.on_node_updated = on_node_updated

    try:
        print(f"🚀 Starting discovery service for node: {discovery.node_id}")
        print(f"   Service type: {discovery.service_type}")
        print(f"   Broadcast port: {discovery.broadcast_port}")
        print(f"   Local IP: {discovery.local_node.ip_address}")
        print()

        # Start the discovery service
        discovery.start()

        # Keep running and show discovered nodes periodically
        while True:
            time.sleep(15)
            
            nodes = discovery.get_discovered_nodes()
            print(f"📊 Currently discovered {len(nodes)} nodes:")
            for node in nodes:
                print(f"   - {node.node_id} at {node.ip_address} (last seen: {node.last_seen})")
            print()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down discovery service...")
    finally:
        discovery.stop()
        print("✅ Discovery service stopped")


if __name__ == "__main__":
    main()
