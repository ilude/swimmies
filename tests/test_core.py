"""Tests for swimmies library core functionality."""

from swimmies.core import hello_world, parse_dns_record, validate_domain_name


def test_hello_world(capfd):
    """Test hello_world function output."""
    hello_world()
    captured = capfd.readouterr()
    assert "Hello from swimmies core!" in captured.out


def test_parse_dns_record():
    """Test DNS record parsing."""
    result = parse_dns_record("example.com")
    assert result["raw"] == "example.com"
    assert result["parsed"] is True


def test_validate_domain_name():
    """Test domain name validation."""
    assert validate_domain_name("example.com") is True
    assert validate_domain_name("sub.example.com") is True
    assert validate_domain_name("invalid") is False
    assert validate_domain_name("") is False
