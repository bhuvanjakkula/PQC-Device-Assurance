"""
Binary analyzer: examines structure, headers, entropy, sections, and memory budgets.
"""

from __future__ import annotations

import math
from models.firmware import BinarySection, ComponentEvidence


def calculate_entropy(data: bytes) -> float:
    """Calculates Shannon entropy of data (0.0 to 8.0)."""
    if not data:
        return 0.0
    freq: dict[int, int] = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    length = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def detect_components(image: bytes) -> list[ComponentEvidence]:
    """Detects embedded software libraries, RTOS kernels, and crypto stacks."""
    components: list[ComponentEvidence] = []

    signatures: dict[str, tuple[str, list[bytes], int]] = {
        "mbedTLS": ("3.4.1", [b"mbedtls_", b"MBEDTLS_"], 38 * 1024),
        "WolfSSL": ("5.6.0", [b"wolfSSL_", b"WOLFSSL_"], 42 * 1024),
        "FreeRTOS": ("10.5.1", [b"vTaskStartScheduler", b"xTaskCreate"], 14 * 1024),
        "Zephyr": ("3.5.0", [b"z_cstart", b"k_thread_create"], 32 * 1024),
        "MCUboot": ("2.0.0", [b"BOOT_MAGIC", b"mcuboot"], 24 * 1024),
        "lwIP": ("2.1.3", [b"lwip_init", b"tcp_connect"], 28 * 1024),
    }

    for name, (ver, patterns, size_est) in signatures.items():
        found = False
        for p in patterns:
            if p in image:
                found = True
                break
        if found:
            components.append(
                ComponentEvidence(
                    name=name,
                    version=ver,
                    size_estimate_bytes=size_est,
                    crypto_symbols=[p.decode("latin1", errors="ignore") for p in patterns],
                )
            )

    return components


def decompose_sections(image: bytes, header_size: int = 256) -> list[BinarySection]:
    """
    Decomposes raw binary firmware into logical firmware sections.
    """
    total = len(image)
    if total <= header_size:
        return [BinarySection(".raw", total, 0, "r-x")]

    # Heuristic layout for standard embedded binary images:
    # [Header: 0..header_size] [Text: 60%] [Data/Constants: 35%] [Signature Block: Remaining]
    sig_block_size = min(512, max(64, total // 32))
    payload_size = total - header_size - sig_block_size

    text_size = int(payload_size * 0.70)
    rodata_size = payload_size - text_size

    sections = [
        BinarySection(".header", header_size, 0, "r--"),
        BinarySection(".text", text_size, header_size, "r-x"),
        BinarySection(".rodata", rodata_size, header_size + text_size, "r--"),
        BinarySection(".sig_block", sig_block_size, total - sig_block_size, "r--"),
    ]
    return sections
