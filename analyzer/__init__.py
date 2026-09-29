"""
Analyzer package initialization.
"""

from analyzer.firmware import FirmwareAnalyzer
from analyzer.crypto import scan_crypto_constants, infer_active_scheme
from analyzer.binary import calculate_entropy, detect_components, decompose_sections
from analyzer.bootloader import analyze_boot_envelope

__all__ = [
    "FirmwareAnalyzer",
    "scan_crypto_constants",
    "infer_active_scheme",
    "calculate_entropy",
    "detect_components",
    "decompose_sections",
    "analyze_boot_envelope",
]
