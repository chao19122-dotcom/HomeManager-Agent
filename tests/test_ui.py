import json
from app import send, clear_chat, reset_devices, status_panel, build_app
from device_state import Session


def test_ui_config_missing_is_honest(monkeypatch, tmp_path):
    from config import Settings
    import app
    monkeypatch.setattr(app, "ROOT", tmp_path)
    monkeypatch.setattr(Settings, "load", lambda: Settings(api_key=""))
    out = send("关闭客厅灯", [], Session())
    assert out[2].devices.lights["客厅"]["on"]
    assert "DEEPSEEK_API_KEY" in out[1][-1]["content"]
    assert out[2].logs[-1]["mode"] == "not_called"


def test_ui_resets_and_html_escape(monkeypatch, tmp_path):
    import app
    monkeypatch.setattr(app, "ROOT", tmp_path)
    s = Session(); s.devices.music["track"] = "<script>alert(1)</script>"
    assert "<script>" not in status_panel(s)
    s.devices.locked = False
    s.messages.append({"role": "user", "content": "hi"})
    assert clear_chat(s)[0] == [] and not s.devices.locked
    reset_devices(s)
    assert s.devices.locked and not s.messages


def test_gradio_builds():
    app = build_app()
    assert app.config["title"] == "HomeManager 智能家居管家 Agent"
