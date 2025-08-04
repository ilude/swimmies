"""Core utilities for swimmies library."""


def hello_world() -> None:
    """Print a friendly greeting from swimmies."""
    print("Hello from swimmies core!")


def parse_dns_record(record: str) -> dict:
    """Parse a DNS record string into components."""
    # Placeholder for future DNS record parsing functionality
    return {"raw": record, "parsed": True}


def validate_domain_name(domain: str) -> bool:
    """Validate a domain name according to RFC standards."""
    # Placeholder for future domain validation
    return len(domain) > 0 and "." in domain
