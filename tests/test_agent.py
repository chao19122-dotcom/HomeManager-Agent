import csv
import json
from datetime import timedelta
from agent import HomeAgent, export_logs, trim_history, DeepSeekModel
from config import Settings
from device_state import Session, now
from tests.fakes import ScriptedModel, calls, text
import pytest


def run(responses, command="测试", session=None, settings=None):
    session = session or Session()
    model = ScriptedModel(*responses)
    record = HomeAgent(model, settings, audit_dir=None).run(session, command)
    return record, session, model


def test_A_single_light_and_explicit_graph():
    r, s, m = run([calls(("light_control_tool", {"room": "客厅", "action": "off"})), text()], "关闭客厅灯")
    assert not s.devices.lights["客厅"]["on"] and s.devices.lights["卧室"]["on"]
    assert len(r["actions"]) == 1
    graph = HomeAgent(m, audit_dir=None).graph.get_graph()
    assert {"llm_decision", "tool_execution", "state_update", "llm_summary"} <= set(graph.nodes)


def test_B_brightness():
    r, s, _ = run([calls(("light_control_tool", {"room": "卧室", "action": "brightness", "brightness": 30})), text()], "把卧室灯亮度设置为30%")
    assert s.devices.lights["卧室"] == {"on": True, "brightness": 30}


def test_C_multi_tools():
    target = (now() + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0).isoformat()
    r, s, _ = run([calls(("light_control_tool", {"room": "全部", "action": "off"}),
                        ("lock_control_tool", {"action": "lock"}),
                        ("alarm_control_tool", {"action": "set", "time": target, "time_evidence": "明早7点"})), text()],
                  "我要睡觉了，关掉灯、锁好门，明早7点叫我")
    assert len(r["actions"]) == 3 and all(a["status"] == "success" for a in r["actions"])
    assert all(not l["on"] for l in s.devices.lights.values()) and s.devices.locked
    assert s.devices.alarms[0]["time"] == target


def test_D_status():
    r, s, _ = run([calls(("get_device_status_tool", {})), text()], "现在家里的设备是什么状态")
    assert r["actions"][0]["observation"]["data"] == s.devices.snapshot()


def test_E_alarm():
    target = (now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0).isoformat()
    r, s, _ = run([calls(("alarm_control_tool", {"action": "set", "time": target, "time_evidence": "明天早上8点"})), text()], "设置明天早上8点的闹钟")
    assert s.devices.alarms[0]["time"] == target


def test_F_chat_no_mutation():
    s = Session(); before = s.devices.snapshot()
    r, _, _ = run([text("你好！")], "你好", s)
    assert not r["actions"] and s.devices.snapshot() == before


def test_G_unlock_confirmation():
    r, s, _ = run([calls(("lock_control_tool", {"action": "unlock"})), text("门已打开")], "把门打开")
    assert s.devices.locked and s.pending_unlock_at
    assert "confirmation_required" in r["reply"] and "门已打开" not in r["reply"]
    r, s, _ = run([calls(("lock_control_tool", {"action": "unlock"})), text()], "确认模拟解锁", s)
    assert not s.devices.locked and s.pending_unlock_at is None


@pytest.mark.parametrize("prior,expired", [(False, False), (True, True)])
def test_confirmation_without_pending_or_expired(prior, expired):
    s = Session()
    if prior:
        s.pending_unlock_at = now() - timedelta(seconds=121)
    r, s, _ = run([calls(("lock_control_tool", {"action": "unlock"})), text()], "确认模拟解锁", s)
    assert s.devices.locked


def test_unrelated_input_clears_confirmation():
    s = Session(); s.pending_unlock_at = now()
    run([text("你好")], "你好", s)
    assert s.pending_unlock_at is None


def test_H_cancel_existing_and_empty():
    s = Session(); s.devices.alarms.append({"id": "test", "time": "2099-01-01T07:00:00+08:00"})
    r, s, _ = run([calls(("alarm_control_tool", {"action": "cancel"})), text()], "取消闹钟", s)
    assert not s.devices.alarms and r["status"] == "success"
    r, _, _ = run([calls(("alarm_control_tool", {"action": "cancel"})), text("取消成功")], "取消闹钟", s)
    assert r["status"] == "needs_attention" and "not_found" in r["reply"]


@pytest.mark.parametrize("response", [RuntimeError("credential must never leak"), {"role": "assistant", "tool_calls": "bad"}, calls(("bad_tool", {})), calls(("light_control_tool", {"room": "卧室", "action": "brightness", "brightness": 200}))])
def test_errors_honest_and_no_mutation(response):
    s = Session(); before = s.devices.snapshot()
    r, s, _ = run([response, text("已成功")], session=s)
    assert s.devices.snapshot() == before and r["status"] != "success"
    assert "已成功" not in r["reply"] and "credential" not in json.dumps(r)


def test_invalid_json():
    response = calls(("light_control_tool", {}))
    response["tool_calls"][0]["function"]["arguments"] = "not json"
    r, _, _ = run([response, text()])
    assert r["actions"][0]["status"] == "validation_error"


def test_model_failure_after_tool_keeps_actual_success():
    r, s, _ = run([calls(("light_control_tool", {"room": "客厅", "action": "off"})), RuntimeError("offline")])
    assert r["status"] == "model_error" and not s.devices.lights["客厅"]["on"]
    assert "success" in r["reply"] and "响应失败" in r["reply"]


def test_round_limit():
    response = calls(("get_device_status_tool", {}))
    r, _, m = run([response, response, response, text()])
    assert len(r["actions"]) == 3 and "上限" in r["reply"]
    assert len(m.requests) == 4 and not m.requests[-1]["use_tools"]


def test_call_batch_limit():
    r, _, _ = run([calls(*[("get_device_status_tool", {})] * 9), text()])
    assert r["actions"][-1]["status"] == "limit_exceeded"
    assert sum(a["status"] == "success" for a in r["actions"]) == 8


def test_export_persist_history(tmp_path):
    s = Session(); model = ScriptedModel(text("你好"))
    r = HomeAgent(model, audit_dir=tmp_path).run(s, "=你好")
    stored = json.loads((tmp_path / s.session_id / "interactions.json").read_text(encoding="utf-8"))
    assert stored == s.logs
    assert json.loads(open(export_logs(s, tmp_path), encoding="utf-8").read()) == s.logs
    with open(export_logs(s, tmp_path, "csv"), encoding="utf-8-sig", newline="") as stream:
        assert list(csv.DictReader(stream))[0]["user_input"].startswith("'=")
    history = sum(([{"role": "user", "content": str(i)}, {"role": "assistant", "content": "hi"}] for i in range(12)), [])
    assert trim_history(history)[0]["content"] == "4"


def test_missing_key_is_not_mock():
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        DeepSeekModel(Settings(api_key=""))


def test_input_validation():
    with pytest.raises(ValueError):
        HomeAgent(ScriptedModel(), audit_dir=None).run(Session(), " ")
