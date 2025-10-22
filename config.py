from dataclasses import dataclass, field
from typing import Optional, Sequence

@dataclass(frozen=True)
class Credentials:
    """User credentials (madridista)."""
    numero: Optional[str] = None
    contrasena: Optional[str] = None


@dataclass(frozen=True)
class LaunchOptions:
    """High-level options controlling how browsers are launched."""
    is_nopecha: bool = False
    is_madridista: bool = False
    is_vpn: bool = False
    browsers_amount: int = 1
    adspower_api: Optional[str] = None
    adspower_ids: Sequence[str] = field(default_factory=tuple)
    proxy_list: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration for a run."""
    initial_url: str
    credentials: Credentials
    options: LaunchOptions
