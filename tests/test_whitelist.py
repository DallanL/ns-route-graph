import pytest
import json
import os
import tempfile
import time
from fastapi import HTTPException
from security import DomainWhitelist


@pytest.fixture
def whitelist_file():
    # Create a temp file
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w") as f:
        json.dump({"allowed_domains": ["api.netsapiens.com", "*.trusted.com"]}, f)
    yield path
    os.remove(path)


def test_whitelist_exact_match(whitelist_file):
    wl = DomainWhitelist(whitelist_file)
    assert wl.is_allowed("https://api.netsapiens.com") is True
    assert wl.is_allowed("http://api.netsapiens.com") is True
    # Test without scheme
    assert wl.is_allowed("api.netsapiens.com") is True


def test_whitelist_wildcard(whitelist_file):
    wl = DomainWhitelist(whitelist_file)
    assert wl.is_allowed("https://client1.trusted.com") is True
    assert wl.is_allowed("https://sub.client2.trusted.com") is True


def test_whitelist_denial(whitelist_file):
    wl = DomainWhitelist(whitelist_file)
    assert wl.is_allowed("https://evil.com") is False
    assert wl.is_allowed("https://netsapiens.com") is False  # Missing api. prefix


def test_whitelist_hot_reload(whitelist_file):
    wl = DomainWhitelist(whitelist_file)
    assert wl.is_allowed("https://new-client.com") is False

    # Update file
    time.sleep(0.1)  # Ensure mtime changes
    with open(whitelist_file, "w") as f:
        json.dump(
            {
                "allowed_domains": [
                    "api.netsapiens.com",
                    "*.trusted.com",
                    "new-client.com",
                ]
            },
            f,
        )

    # Should now pass
    assert wl.is_allowed("https://new-client.com") is True


def test_validate_or_raise(whitelist_file):
    wl = DomainWhitelist(whitelist_file)
    # Should not raise
    wl.validate_or_raise("https://api.netsapiens.com")

    # Should raise
    with pytest.raises(HTTPException) as excinfo:
        wl.validate_or_raise("https://evil.com")
    assert excinfo.value.status_code == 403
