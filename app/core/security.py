import socket
import ipaddress
from urllib.parse import urlparse
from app.core.exceptions import SSRException
from app.core.logging import logger


def is_safe_url(url: str, allow_local_for_dev: bool = False) -> bool:
    """
    Validates URL to protect against SSRF (Server-Side Request Forgery).
    Rejects private networks, loopback, link-local, multicast, metadata endpoints.
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise SSRException(f"Invalid URL scheme: '{parsed.scheme}'. Only http and https are permitted.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRException("Invalid URL: missing hostname.")

        if allow_local_for_dev and (hostname in ("localhost", "127.0.0.1", "testserver") or hostname.endswith(".local")):
            return True

        # Check for obvious forbidden hostnames
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal", "169.254.169.254"):
            raise SSRException(f"Target host '{hostname}' is prohibited due to SSRF security policies.")

        # Resolve IP addresses
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = ipaddress.ip_address(ip_str)

            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise SSRException(f"Host '{hostname}' resolved to prohibited IP address '{ip_str}'.")

        return True
    except SSRException:
        raise
    except socket.gaierror as e:
        raise SSRException(f"Failed to resolve hostname '{parsed.hostname}': {str(e)}")
    except Exception as e:
        raise SSRException(f"URL validation failed: {str(e)}")
