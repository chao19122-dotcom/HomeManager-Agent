from datetime import timedelta
import pytest
from device_state import DeviceState, Session, now
from tools import execute_tool, tool_schemas


def test_five_structured_tools():
    assert len(tool_schemas()) == 5
    assert all(s["function"]["parameters"]["additionalProperties"] is False for s in tool_schemas())


@pytest.mark.parametrize("brightness", [-1, 101, 30.5, True, "30", None])
def test_brightness_invalid_no_mutation(brightness):
    d = DeviceState(); before = d.snapshot()
    r = execute_tool("light_control_tool", {"room": "卧室", "action": "brightness", "brightness": brightness}, d)
    assert r["status"] == "validation_error"
    assert d.snapshot() == before


@pytest.mark.parametrize("room", ["厨房", "不存在", ""])
def test_unknown_room(room):
    assert execute_tool("light_control_tool", {"room": room, "action": "off"}, DeviceState())["status"] == "validation_error"


def test_light_zero_and_turn_on():
    d = DeviceState()
    execute_tool("light_control_tool", {"room": "全部", "action": "brightness", "brightness": 0}, d)
    assert all(not v["on"] for v in d.lights.values())
    execute_tool("light_control_tool", {"room": "客厅", "action": "on"}, d)
    assert d.lights["客厅"] == {"on": True, "brightness": 80}


def test_unlock_cannot_inject_confirmation():
    d = DeviceState()
    assert execute_tool("lock_control_tool", {"action": "unlock", "confirmed": True}, d)["status"] == "validation_error"
    assert execute_tool("lock_control_tool", {"action": "unlock"}, d)["status"] == "confirmation_required"
    assert d.locked


@pytest.mark.parametrize("args,expected", [
    ({"action": "set"}, "needs_input"),
    ({"action": "set", "time": "2099-01-01T08:00:00+08:00", "time_evidence": "8点"}, "needs_input"),
    ({"action": "set", "time": "invalid", "time_evidence": "8点"}, "validation_error"),
    ({"action": "set", "time": "2020-01-01T08:00:00+08:00", "time_evidence": "8点"}, "validation_error"),
    ({"action": "set", "time": "2099-01-01T08:00:00", "time_evidence": "8点"}, "validation_error"),
])
def test_alarm_invalid(args, expected):
    user = "设置闹钟" if expected == "needs_input" else "8点"
    d = DeviceState()
    assert execute_tool("alarm_control_tool", args, d, user_text=user)["status"] == expected
    assert not d.alarms


def test_alarm_create_deduplicate_cancel():
    d = DeviceState(); time = (now() + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0).isoformat()
    args = {"action": "set", "time": time, "time_evidence": "明天早上8点"}
    for _ in range(2):
        assert execute_tool("alarm_control_tool", args, d, user_text="设置明天早上8点的闹钟")["status"] == "success"
    assert len(d.alarms) == 1
    assert execute_tool("alarm_control_tool", {"action": "list"}, d)["data"]["alarms"]
    assert execute_tool("alarm_control_tool", {"action": "cancel", "alarm_id": "bad"}, d)["status"] == "not_found"
    assert len(d.alarms) == 1
    assert execute_tool("alarm_control_tool", {"action": "cancel"}, d)["data"]["cancelled"] == 1
    assert execute_tool("alarm_control_tool", {"action": "cancel"}, d)["status"] == "not_found"


def test_music_lifecycle():
    d = DeviceState()
    assert execute_tool("music_control_tool", {"action": "pause"}, d)["status"] == "not_found"
    for action in ["play", "pause", "next", "status"]:
        assert execute_tool("music_control_tool", {"action": action}, d)["status"] == "success"
    assert d.music == {"status": "playing", "track": "钢琴·月色"}


def test_unknown_tool_and_session_isolation():
    a, b = Session(), Session()
    execute_tool("light_control_tool", {"room": "全部", "action": "off"}, a.devices)
    assert b.devices.lights["客厅"]["on"]
    assert execute_tool("invented_tool", {}, a.devices)["status"] == "unknown_tool"
    snapshot = execute_tool("get_device_status_tool", {}, a.devices)["data"]
    snapshot["lights"]["客厅"]["on"] = True
    assert not a.devices.lights["客厅"]["on"]


def test_tool_exception_is_atomic(monkeypatch):
    import tools
    def broken(d, a, **context):
        d.locked = False
        raise RuntimeError("failure after mutation")
    monkeypatch.setitem(tools.HANDLERS, "lock_control_tool", broken)
    d = DeviceState()
    assert execute_tool("lock_control_tool", {"action": "lock"}, d)["status"] == "tool_error"
    assert d.locked
