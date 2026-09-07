"""
Secure storage and image URI resolver for ML inference service.
Handles local paths, storage:// URIs, and Cloudflare R2 URLs with SSRF protection.
"""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse
import httpx

# Find project root directory relative to this file
# ML_MODEL/src/storage/resolver.py -> ML_MODEL -> project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_MODEL_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(ML_MODEL_DIR, ".."))

STORAGE_INCOMING = os.environ.get(
    "STORAGE_INCOMING_DIR",
    os.path.join(PROJECT_ROOT, "storage", "incoming")
)
os.makedirs(STORAGE_INCOMING, exist_ok=True)

# Configured R2 / Storage domains for SSRF validation
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "").strip()
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "").strip()
ALLOWED_HOSTS = set(
    filter(
        None,
        [
            urlparse(R2_PUBLIC_BASE_URL).netloc if R2_PUBLIC_BASE_URL else None,
            urlparse(R2_ENDPOINT_URL).netloc if R2_ENDPOINT_URL else None,
            os.environ.get("ALLOWED_STORAGE_HOST", "").strip() or None,
            "r2.dev",
            "cloudflarestorage.com",
        ]
    )
)


def _is_safe_host(hostname: str) -> bool:
    """Check if the given hostname is an authorized Cloudflare R2 / storage host."""
    if not hostname:
        return False
    hostname = hostname.lower()
    for allowed in ALLOWED_HOSTS:
        if hostname == allowed.lower() or hostname.endswith("." + allowed.lower()):
            return True
    return False


def resolve_image_path(image_uri: str, download_timeout: int = 30) -> str:
    """
    Resolve an image URI to a locally accessible file path for ML inference.

    Supported schemes:
    1. Direct local file path (e.g. C:/.../image.tif or ./storage/incoming/image.tif)
    2. storage:// scheme (e.g. storage://incoming/image.tif or storage://image.tif)
    3. file:// scheme (e.g. file:///path/to/image.tif)
    4. Verified Cloudflare R2 HTTPS URLs (checks local cache first, then securely downloads)

    Args:
        image_uri: URI or path to the TIFF image
        download_timeout: Timeout in seconds for remote downloads

    Returns:
        Absolute local path to the existing TIFF image

    Raises:
        ValueError: If URI is invalid or attempts SSRF against unauthorized domains
        FileNotFoundError: If the image file cannot be found
    """
    if not image_uri or not isinstance(image_uri, str):
        raise ValueError("image_uri must be a non-empty string")

    cleaned_uri = image_uri.strip()

    # 1. Direct local file path
    if os.path.isabs(cleaned_uri) and os.path.exists(cleaned_uri):
        return os.path.abspath(cleaned_uri)

    # Check relative to current working directory
    if os.path.exists(cleaned_uri):
        return os.path.abspath(cleaned_uri)

    # 2. file:// scheme
    if cleaned_uri.startswith("file://"):
        file_path = cleaned_uri[7:]
        # On Windows file:///C:/path -> C:/path
        if file_path.startswith("/") and len(file_path) > 2 and file_path[2] == ":":
            file_path = file_path[1:]
        if os.path.exists(file_path):
            return os.path.abspath(file_path)
        raise FileNotFoundError(f"Local file not found from file:// URI: {file_path}")

    # 3. storage:// scheme
    if cleaned_uri.startswith("storage://"):
        rel_path = cleaned_uri[10:].lstrip("/\\")
        # Strip incoming/ if present to check both locations
        filename = os.path.basename(rel_path)

        candidates = [
            os.path.join(STORAGE_INCOMING, filename),
            os.path.join(PROJECT_ROOT, "storage", rel_path),
            os.path.join(PROJECT_ROOT, rel_path),
            os.path.join("/mnt/storage", rel_path),  # Docker/Linux mount fallback
        ]

        for cand in candidates:
            if os.path.exists(cand):
                return os.path.abspath(cand)

        # Also check relative to ML_MODEL_DIR
        cand_ml = os.path.join(ML_MODEL_DIR, rel_path)
        if os.path.exists(cand_ml):
            return os.path.abspath(cand_ml)

        raise FileNotFoundError(
            f"Image not found in storage for URI '{cleaned_uri}'. "
            f"Looked in: {', '.join(candidates)}"
        )

    # 4. HTTPS / HTTP URLs
    parsed = urlparse(cleaned_uri)
    if parsed.scheme in ("http", "https"):
        hostname = parsed.hostname or ""

        # SSRF Protection: verify host is an allowed R2 domain
        if not _is_safe_host(hostname):
            raise ValueError(
                f"Security error: Remote domain '{hostname}' is not an authorized R2 storage host. "
                f"Allowed hosts: {sorted(list(ALLOWED_HOSTS))}"
            )

        # Check if already cached in storage/incoming/
        filename = os.path.basename(parsed.path)
        if not filename:
            raise ValueError(f"Invalid URL without filename: {cleaned_uri}")

        cached_path = os.path.join(STORAGE_INCOMING, filename)
        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
            return os.path.abspath(cached_path)

        # Download from authorized R2 URL
        try:
            with httpx.Client(timeout=download_timeout, follow_redirects=True) as client:
                resp = client.get(cleaned_uri)
                resp.raise_for_status()
                with open(cached_path, "wb") as f:
                    f.write(resp.content)
            return os.path.abspath(cached_path)
        except httpx.HTTPError as e:
            raise FileNotFoundError(f"Failed to retrieve image from R2 URL '{cleaned_uri}': {str(e)}")

    # 5. Check if filename exists in storage/incoming
    fallback_in_storage = os.path.join(STORAGE_INCOMING, os.path.basename(cleaned_uri))
    if os.path.exists(fallback_in_storage):
        return os.path.abspath(fallback_in_storage)

    raise FileNotFoundError(f"Could not resolve image_uri: '{image_uri}'")
