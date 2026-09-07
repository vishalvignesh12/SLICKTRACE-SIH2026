import os
import tempfile
import pytest
from src.storage.resolver import resolve_image_path, _is_safe_host


def test_resolve_local_existing_file():
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tf:
        tf.write(b"dummy tiff data")
        temp_path = tf.name

    try:
        resolved = resolve_image_path(temp_path)
        assert os.path.exists(resolved)
        assert os.path.abspath(temp_path) == resolved
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_resolve_file_scheme():
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tf:
        tf.write(b"dummy tiff data")
        temp_path = tf.name

    try:
        file_uri = f"file:///{temp_path.replace(os.sep, '/')}"
        resolved = resolve_image_path(file_uri)
        assert os.path.exists(resolved)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_resolve_storage_scheme(tmp_path, monkeypatch):
    test_storage = tmp_path / "incoming"
    test_storage.mkdir(parents=True)
    test_file = test_storage / "sample_scene.tif"
    test_file.write_bytes(b"dummy sar data")

    monkeypatch.setattr("src.storage.resolver.STORAGE_INCOMING", str(test_storage))

    resolved = resolve_image_path("storage://incoming/sample_scene.tif")
    assert os.path.exists(resolved)
    assert resolved == str(test_file)


def test_ssrf_protection_rejects_untrusted_host():
    untrusted_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "https://evil-attacker.com/malicious.tif",
        "http://localhost:8000/internal-data.tif",
        "https://storage.googleapis.com/untrusted/image.tif",
    ]

    for url in untrusted_urls:
        with pytest.raises(ValueError, match="Security error: Remote domain"):
            resolve_image_path(url)


def test_safe_host_validation():
    assert _is_safe_host("pub-abc.r2.dev") is True
    assert _is_safe_host("account.r2.cloudflarestorage.com") is True
    assert _is_safe_host("untrusted-site.com") is False
    assert _is_safe_host("") is False


def test_missing_image_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        resolve_image_path("storage://incoming/non_existent_file_99999.tif")


def test_invalid_uri_raises_valueerror():
    with pytest.raises(ValueError):
        resolve_image_path("")
    with pytest.raises(ValueError):
        resolve_image_path(None)
