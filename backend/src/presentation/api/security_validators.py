"""API istekleri için ağ ve alan doğrulama yardımcıları."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlparse

DEFAULT_SCAN_ALLOWED_CIDRS = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8"
MAX_SCAN_ADDRESSES = int(os.environ.get("MAX_SCAN_ADDRESSES", "256"))


def validate_port(value: int | None, default: int) -> int:
    """TCP/UDP port değerini 1-65535 aralığında doğrular."""
    port = default if value is None else int(value)
    if port < 1 or port > 65535:
        raise ValueError("Port 1-65535 aralığında olmalıdır.")
    return port


def validate_host(value: str) -> str:
    """Host/IP alanını şema, path ve boşluk içermeyecek şekilde doğrular."""
    host = value.strip()
    if not host:
        raise ValueError("Host boş olamaz.")
    if len(host) > 255:
        raise ValueError("Host en fazla 255 karakter olabilir.")
    parsed = urlparse(host)
    if parsed.scheme or "/" in host or "\\" in host or any(ch.isspace() for ch in host):
        raise ValueError("Host yalnızca IP adresi veya hostname olmalıdır.")
    return host


def validate_scan_target(value: str) -> str:
    """Tekil IP/hostname veya CIDR tarama hedefini allowlist ve boyut sınırıyla doğrular."""
    target = value.strip()
    if not target:
        raise ValueError("Tarama hedefi boş olamaz.")
    if "/" not in target:
        return validate_host(target)

    try:
        network = ipaddress.ip_network(target, strict=False)
    except ValueError as exc:
        raise ValueError("Tarama hedefi geçerli IP/CIDR olmalıdır.") from exc

    if network.num_addresses > MAX_SCAN_ADDRESSES:
        raise ValueError(f"Tarama aralığı en fazla {MAX_SCAN_ADDRESSES} adres içerebilir.")

    allowed = [
        ipaddress.ip_network(item.strip(), strict=False)
        for item in os.environ.get("SCAN_ALLOWED_CIDRS", DEFAULT_SCAN_ALLOWED_CIDRS).split(",")
        if item.strip()
    ]
    if allowed and not any(network.subnet_of(item) for item in allowed):
        raise ValueError("Tarama aralığı izin verilen ağ listesinde değil.")
    return str(network)
