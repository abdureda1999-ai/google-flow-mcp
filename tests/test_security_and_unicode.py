from __future__ import annotations

import os
from pathlib import Path
import pytest

from flow_mcp.browser_engine import (
    _clear_stale_singleton_lock,
    _slugify,
    get_max_credits_per_call,
)
from flow_mcp.engine import (
    slugify,
    validate_safe_input_path,
    validate_safe_output_path,
)
from flow_mcp.server import _BROWSER_LOCK, _VIDEO_LOCK, _build_widget_csp_domains


def test_unicode_and_arabic_slugify_preserves_script() -> None:
    ar = "إعلان سينمائي لزجاجة عطر فاخرة في الصحراء!"
    slug_engine = slugify(ar)
    slug_browser = _slugify(ar)
    assert "إعلان_سينمائي" in slug_engine
    assert slug_engine == slug_browser
    assert slugify("مُنتَجٌ عَرَبِيّ") == "منتج_عربي"
    assert slugify("!!!") == "flow_asset"
    assert _slugify("!!!") == "flow_output"


def test_sensitive_paths_blocked_unconditionally(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FLOW_STRICT_MEDIA_SANDBOX", "0")
    ssh_key = os.path.expanduser("~/.ssh/id_rsa")
    with pytest.raises(ValueError, match="sensitive path"):
        validate_safe_input_path(ssh_key)
    with pytest.raises(ValueError, match="sensitive path"):
        validate_safe_output_path("~/.ssh/authorized_keys")
    with pytest.raises(ValueError, match="sensitive path"):
        validate_safe_output_path("~/.google-flow-mcp/secret")


def test_strict_media_sandbox_blocks_outside_media_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    inside = media_dir / "frame.png"
    inside.write_bytes(b"png")

    monkeypatch.setenv("FLOW_MEDIA_DIR", str(media_dir))
    monkeypatch.setenv("FLOW_STRICT_MEDIA_SANDBOX", "1")

    assert validate_safe_input_path(str(inside)) == os.path.abspath(str(inside))
    assert validate_safe_output_path(str(media_dir / "out.mp4")) == os.path.abspath(str(media_dir / "out.mp4"))

    with pytest.raises(ValueError, match="FLOW_MEDIA_DIR"):
        validate_safe_input_path(str(outside))
    with pytest.raises(ValueError, match="FLOW_MEDIA_DIR"):
        validate_safe_output_path(str(tmp_path / "escape.mp4"))


def test_singleton_lock_preserves_live_process_and_clears_dead(tmp_path: Path) -> None:
    live_lock = tmp_path / "SingletonLock"
    os.symlink(f"localhost-{os.getpid()}", live_lock)
    with pytest.raises(RuntimeError, match="currently in use"):
        _clear_stale_singleton_lock(str(tmp_path))
    assert os.path.lexists(live_lock)

    os.remove(live_lock)
    os.symlink("localhost-99999999", live_lock)
    _clear_stale_singleton_lock(str(tmp_path))
    assert not os.path.lexists(live_lock)


def test_credit_spend_ceilings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLOW_NO_SPEND", raising=False)
    monkeypatch.delenv("FLOW_MAX_CREDITS_PER_CALL", raising=False)
    assert get_max_credits_per_call() is None

    monkeypatch.setenv("FLOW_MAX_CREDITS_PER_CALL", "30")
    assert get_max_credits_per_call() == 30

    monkeypatch.setenv("FLOW_NO_SPEND", "1")
    assert get_max_credits_per_call() == 0


def test_widget_csp_and_shared_browser_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _BROWSER_LOCK is _VIDEO_LOCK
    monkeypatch.setenv("FLOW_NGROK_DOMAIN", "demo-studio.ngrok-free.app")
    monkeypatch.setenv("FLOW_PUBLIC_URL", "https://flow-bridge.example.com/custom")
    domains = _build_widget_csp_domains()
    assert "https://*.trycloudflare.com" in domains
    assert "https://*.ngrok-free.app" in domains
    assert "https://demo-studio.ngrok-free.app" in domains
    assert "https://flow-bridge.example.com" in domains
