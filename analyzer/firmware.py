"""
Firmware Analyzer: Top-level ingestion and analysis orchestrator.
Firmware Release N -> Firmware Analyzer -> Crypto discovery + Binary analysis + Resource estimation
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

from analyzer.binary import calculate_entropy, decompose_sections, detect_components
from analyzer.crypto import infer_active_scheme, scan_crypto_constants
from models.firmware import FirmwareRelease


class FirmwareAnalyzer:
    """
    Ingests and analyzes firmware releases, extracting cryptographic artifacts,
    binary geometry, and resource utilization metrics.
    """

    @staticmethod
    def analyze_bytes(
        image: bytes,
        firmware_id: str = "firmware-release.bin",
        family_id: str = "generic-device",
        version: str = "1.0.0",
        header_size: int = 256,
    ) -> FirmwareRelease:
        sha256_hash = hashlib.sha256(image).hexdigest()
        raw_size = len(image)
        entropy = calculate_entropy(image)

        # 1. Crypto discovery
        findings = scan_crypto_constants(image)

        # 2. Binary and component analysis
        sections = decompose_sections(image, header_size=header_size)
        components = detect_components(image)

        # 3. Resource estimation
        text_size = sum(s.size_bytes for s in sections if s.name == ".text")
        data_size = sum(s.size_bytes for s in sections if s.name == ".rodata")
        # Estimated runtime RAM working set based on data section + stack estimate
        estimated_ram = max(4096, data_size // 4 + 8192)

        return FirmwareRelease(
            firmware_id=firmware_id,
            family_id=family_id,
            version=version,
            raw_size_bytes=raw_size,
            sha256=sha256_hash,
            header_size=header_size,
            text_size=text_size,
            data_size=data_size,
            estimated_ram_usage=estimated_ram,
            findings=findings,
            components=components,
            sections=sections,
            entropy_score=entropy,
        )

    @classmethod
    def analyze_file(
        cls,
        path: Union[str, Path],
        family_id: str = "generic-device",
        version: str = "1.0.0",
        header_size: int = 256,
    ) -> FirmwareRelease:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Firmware binary not found at: {path}")
        image = p.read_bytes()
        return cls.analyze_bytes(
            image=image,
            firmware_id=p.name,
            family_id=family_id,
            version=version,
            header_size=header_size,
        )
