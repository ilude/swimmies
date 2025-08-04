"""
Swimmies - A utility library for Joyride DNS Service

This library provides common utilities and data structures used across
the Joyride DNS ecosystem.
"""

__version__ = "0.1.1"

from .core import hello_world
from .gossip import GossipMessage, GossipNode

__all__ = ["hello_world", "GossipNode", "GossipMessage"]


def main() -> None:
    """CLI entry point for swimmies."""
    hello_world()
