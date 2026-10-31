"""Reproducible A-H results: --mode mock | live. No keyword mock router."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import HomeAgent, DeepSeekModel, export_logs
from config import ROOT, Settings
from device_state import Session, now
from tests.fakes import ScriptedModel, calls, text


def evaluate(live=False, output_dir=None):
    folder = Path(output_dir or ROOT / "results")
    folder.mkdir(parents=True, exist_ok=True)
    mode = "live_api" if live else "mock_scripted"
    config = Settings.load()
    prefix = "live" if live else "mock"
    if live and not config.api_key:
        report = {"mode": mode, "status": "not_run", "reason": "缺少 DEEPSEEK_API_KEY", "passed": 0, "failed": 0, "executed": 0}
        (folder / "live_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    model = DeepSeekModel(config) if live else None
    day = now() + timedelta(days=1)
    time7 = day.replace(hour=7, minute=0, second=0, microsecond=0).isoformat()
    time8 = day.replace(hour=8, minute=0, second=0, microsecond=0).isoformat()
    cases = [
        ("A", "关闭客厅灯", [("light_control_tool", {"room": "客厅", "action": "off"})], lambda s, r: not s.devices.lights["客厅"]["on"], {"light_control_tool"}),
        ("B", "把卧室灯亮度设置为30%", [("light_control_tool", {"room": "卧室", "action": "brightness", "brightness": 30})], lambda s, r: s.devices.lights["卧室"] == {"on": True, "brightness": 30}, {"light_control_tool"}),
        ("C", "我要睡觉了，关掉灯、锁好门，明早7点叫我", [("light_control_tool", {"room": "全部", "action": "off"}), ("lock_control_tool", {"action": "lock"}), ("alarm_control_tool", {"action": "set", "time": time7, "time_evidence": "明早7点"})], lambda s, r: all(not v["on"] for v in s.devices.lights.values()) and s.devices.locked and any(a["time"] == time7 for a in s.devices.alarms), {"light_control_tool", "lock_control_tool", "alarm_control_tool"}),
        ("D", "现在家里的设备是什么状态", [("get_device_status_tool", {})], lambda s, r: r["actions"][0]["observation"]["data"] == s.devices.snapshot(), {"get_device_status_tool"}),
        ("E", "设置明天早上8点的闹钟", [("alarm_control_tool", {"action": "set", "time": time8, "time_evidence": "明天早上8点"})], lambda s, r: any(a["time"] == time8 for a in s.devices.alarms), {"alarm_control_tool"}),
        ("F", "你好", [], lambda s, r: not r["actions"] and s.devices.snapshot() == Session().devices.snapshot(), set()),
        ("G", "把门打开", [("lock_control_tool", {"action": "unlock"})], lambda s, r: s.devices.locked and s.pending_unlock_at is not None and any(a["status"] == "confirmation_required" for a in r["actions"]), {"lock_control_tool"}),
        ("H-existing", "取消闹钟", [("alarm_control_tool", {"action": "cancel"})], lambda s, r: not s.devices.alarms and r["actions"][0]["status"] == "success", {"alarm_control_tool"}),
        ("H-empty", "取消闹钟", [("alarm_control_tool", {"action": "cancel"})], lambda s, r: not s.devices.alarms and r["actions"][0]["status"] == "not_found", {"alarm_control_tool"}),
    ]
    rows, interactions = [], []
    for name, command, script, check, expected_tools in cases:
        session = Session()
        if name == "H-existing":
            session.devices.alarms.append({"id": "seed", "time": time8})
        if name == "C":
            session.devices.locked = False
        current_model = model or ScriptedModel(*([calls(*script)] if script else []), text("模拟脚本固定回复，非真实模型输出。"))
        record = HomeAgent(current_model, config, audit_dir=None).run(session, command)
        interactions.append(record)
        actual_tools = {a["tool_name"] for a in record["actions"]}
        try:
            passed = check(session, record) and actual_tools == expected_tools and record["status"] != "model_error"
        except (IndexError, KeyError):
            passed = False
        rows.append({"case": name, "input": command, "passed": passed, "tool_names": sorted(actual_tools), "status": record["status"]})
    actions = [a for r in interactions for a in r["actions"]]
    successes = sum(a["status"] == "success" for a in actions)
    report = {"mode": mode, "status": "completed", "generated_at": now().isoformat(),
              "model": config.model if live else "ScriptedModel（预设消息夹具，不评估语言理解）",
              "executed": len(rows), "passed": sum(r["passed"] for r in rows), "failed": sum(not r["passed"] for r in rows),
              "tool_calls": len(actions), "tool_successes": successes,
              "tool_success_rate": successes / len(actions) if actions else None,
              "metric_note": "分母包含预期 confirmation_required/not_found；它们是正确受控行为，不计作工具成功。用例通过率另计。",
              "exceptions": [a for a in actions if a["status"] != "success"], "cases": rows}
    (folder / f"{prefix}_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / f"{prefix}_interactions.json").write_text(json.dumps(interactions, ensure_ascii=False, indent=2), encoding="utf-8")
    aggregate = Session(logs=interactions)
    export_logs(aggregate, folder / f"{prefix}_exports", "csv")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    args = parser.parse_args()
    report = evaluate(live=args.mode == "live")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if report.get("failed") or report["status"] == "not_run" else 0)
