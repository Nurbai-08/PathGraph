import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit, urlunsplit

from app.core.errors import AppError

ALLOWED_SCHEMES = {"http", "https"}


def normalize_and_validate_url(value: str) -> str:
    try:
        parsed = urlsplit(value.strip())
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise invalid_url("The URL is malformed.") from error

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise invalid_url("Only HTTP and HTTPS URLs are allowed.")
    if not hostname or parsed.username or parsed.password:
        raise invalid_url("The URL must contain a public host and no credentials.")

    ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    validate_public_hostname(ascii_hostname, port)
    netloc = ascii_hostname
    if port and not is_default_port(parsed.scheme.lower(), port):
        netloc = f"{ascii_hostname}:{port}"

    normalized = SplitResult(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        path=parsed.path or "/",
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(normalized)


def validate_public_hostname(hostname: str, port: int | None = None) -> None:
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise invalid_url("Local and private network addresses are not allowed.")

    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            socket_port = port or 443
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, socket_port, type=socket.SOCK_STREAM)
            }
        except socket.gaierror as error:
            raise invalid_url("The URL host could not be resolved.") from error

    if not addresses or any(not address.is_global for address in addresses):
        raise invalid_url("Local and private network addresses are not allowed.")


def is_default_port(scheme: str, port: int) -> bool:
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)


def invalid_url(message: str) -> AppError:
    return AppError(422, "INVALID_SOURCE_URL", message)
