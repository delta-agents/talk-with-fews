import json

import pytest

from talk_with_fews.app import create_app
from talk_with_fews.routers.setup_connections import setup_env


def _mount_paths(app):
    return {route.path for route in app.routes if route.path.startswith("/mcp/")}


def test_create_app_mounts_all_servers_by_default(monkeypatch):
    monkeypatch.delenv("TALK_WITH_FEWS_SERVERS", raising=False)
    app = create_app()
    assert _mount_paths(app) == {
        "/mcp/TalkWithConfig",
        "/mcp/TalkWithWebservice",
        "/mcp/TalkWithValidator",
    }


def test_create_app_mounts_only_selected_servers():
    app = create_app(["config"])
    assert _mount_paths(app) == {"/mcp/TalkWithConfig"}


def test_create_app_reads_servers_from_env(monkeypatch):
    monkeypatch.setenv("TALK_WITH_FEWS_SERVERS", "config, validator")
    app = create_app()
    assert _mount_paths(app) == {"/mcp/TalkWithConfig", "/mcp/TalkWithValidator"}


def test_create_app_rejects_unknown_server():
    with pytest.raises(ValueError, match="Unknown server"):
        create_app(["config", "nope"])


def test_setup_env_uses_env_dir(tmp_path, monkeypatch):
    tokens = {"abc": {"client_id": "x", "scopes": ["read:data"]}}
    (tmp_path / "tokens.json").write_text(json.dumps(tokens))
    monkeypatch.setenv("TALK_WITH_FEWS_ENV_DIR", str(tmp_path))
    monkeypatch.setenv("STATIC_TOKENS_FILE", "tokens.json")
    assert setup_env() == tokens


def test_setup_env_missing_tokens_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TALK_WITH_FEWS_ENV_DIR", str(tmp_path))
    monkeypatch.setenv("STATIC_TOKENS_FILE", "missing.json")
    with pytest.raises(FileNotFoundError, match="TALK_WITH_FEWS_ENV_DIR"):
        setup_env()
