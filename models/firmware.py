"""
Firmware models representing firmware releases, sections, components,
and discovered cryptographic evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class CryptoFinding:
    algorithm: str
    role: str               # "secure_boot" | "payload" | "transport" | "keystore"
    offset: Optional[int]
    evidence: str
    confidence: float
    used_at_boot: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "role": self.role,
            "offset": self.offset,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 2),
            "used_at_boot": self.used_at_boot,
        }


@dataclass
class BinarySection:
    name: str               # ".text", ".data", ".rodata", ".header", ".sig"
    size_bytes: int
    offset: int
    flags: str = "r-x"


@dataclass
class ComponentEvidence:
    name: str               # e.g., "mbedTLS", "Zephyr RTOS", "FreeRTOS", "LWIP"
    version: Optional[str]
    size_estimate_bytes: int
    crypto_symbols: list[str] = field(default_factory=list)


@dataclass
class FirmwareRelease:
    firmware_id: str
    family_id: str
    version: str
    raw_size_bytes: int
    sha256: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    header_size: int = 256
    text_size: int = 0
    data_size: int = 0
    estimated_ram_usage: int = 0
    findings: list[CryptoFinding] = field(default_factory=list)
    components: list[ComponentEvidence] = field(default_factory=list)
    sections: list[BinarySection] = field(default_factory=list)
    entropy_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "firmware_id": self.firmware_id,
            "family_id": self.family_id,
            "version": self.version,
            "raw_size_bytes": self.raw_size_bytes,
            "sha256": self.sha256,
            "created_at": self.created_at,
            "header_size": self.header_size,
            "text_size": self.text_size,
            "data_size": self.data_size,
            "estimated_ram_usage": self.estimated_ram_usage,
            "findings": [f.to_dict() for f in self.findings],
            "entropy_score": round(self.entropy_score, 3),
        }
