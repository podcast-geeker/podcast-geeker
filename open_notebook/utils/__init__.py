"""
Utils package for Podcast Geeker.

This module intentionally exports symbols lazily to avoid expensive startup
imports (e.g. numpy/cryptography) when callers only need a small subset.
"""

from importlib import import_module
from typing import Dict, Tuple

__all__ = [
    # Chunking
    "CHUNK_SIZE",
    "ContentType",
    "chunk_text",
    "detect_content_type",
    "detect_content_type_from_extension",
    "detect_content_type_from_heuristics",
    # Embedding
    "generate_embedding",
    "generate_embeddings",
    "mean_pool_embeddings",
    # Text utils
    "remove_non_ascii",
    "remove_non_printable",
    "parse_thinking_content",
    "clean_thinking_content",
    # Token utils
    "token_count",
    "token_cost",
    # Version utils
    "compare_versions",
    "get_installed_version",
    "get_version_from_github",
    # Encryption utils
    "decrypt_value",
    "encrypt_value",
]

_EXPORTS: Dict[str, Tuple[str, str]] = {
    # chunking
    "CHUNK_SIZE": (".chunking", "CHUNK_SIZE"),
    "ContentType": (".chunking", "ContentType"),
    "chunk_text": (".chunking", "chunk_text"),
    "detect_content_type": (".chunking", "detect_content_type"),
    "detect_content_type_from_extension": (
        ".chunking",
        "detect_content_type_from_extension",
    ),
    "detect_content_type_from_heuristics": (
        ".chunking",
        "detect_content_type_from_heuristics",
    ),
    # embedding
    "generate_embedding": (".embedding", "generate_embedding"),
    "generate_embeddings": (".embedding", "generate_embeddings"),
    "mean_pool_embeddings": (".embedding", "mean_pool_embeddings"),
    # text utils
    "remove_non_ascii": (".text_utils", "remove_non_ascii"),
    "remove_non_printable": (".text_utils", "remove_non_printable"),
    "parse_thinking_content": (".text_utils", "parse_thinking_content"),
    "clean_thinking_content": (".text_utils", "clean_thinking_content"),
    # token utils
    "token_count": (".token_utils", "token_count"),
    "token_cost": (".token_utils", "token_cost"),
    # version utils
    "compare_versions": (".version_utils", "compare_versions"),
    "get_installed_version": (".version_utils", "get_installed_version"),
    "get_version_from_github": (".version_utils", "get_version_from_github"),
    # encryption utils
    "decrypt_value": (".encryption", "decrypt_value"),
    "encrypt_value": (".encryption", "encrypt_value"),
}


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attr_name = target
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals().keys()) | set(__all__))
