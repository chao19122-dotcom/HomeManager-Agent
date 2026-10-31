"""Five expert tools, strict schemas, uniform observations and safety checks."""
from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4
import copy
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from device_state import DeviceState, TZ, now


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LightArgs(Args):
    room: Literal["客厅", "卧室", "全部"]
    action: Literal["on", "off", "brightness", "status"]
    brightness: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def consistent(self):
        if self.action == "brightness" and self.brightness is None:
            raise ValueError("设置亮度必须提供 0~100 的整数 brightness")
        if self.action != "brightness" and self.brightness is not None:
            raise ValueError("仅 brightness 操作接受 brightness 参数")
        return self


class LockArgs(Args):
    action: Literal["status", "lock", "unlock"]


class AlarmArgs(Args):
    action: Literal["set", "list", "cancel"]
    time: str | None = Field(default=None, description="Asia/Shanghai 的 ISO8601 时间，含 +08:00")
    time_evidence: str | None = Field(default=None, description="逐字引用当前用户指定时间的片段；禁止编造")
    alarm_id: str | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.action != "set" and (self.time is not None or self.time_evidence is not None):
            raise ValueError("只有 set 接受 time 和 time_evidence")
        if self.action != "cancel" and self.alarm_id is not None:
            raise ValueError("只有 cancel 接受 alarm_id")
        return self


class MusicArgs(Args):
    action: Literal["play", "pause", "next", "status"]
    track: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def consistent(self):
        if self.action != "play" and self.track is not None:
            raise ValueError("只有 play 接受 track")
        return self


class StatusArgs(Args):
    pass


REGISTRY = {
    "light_control_tool": (LightArgs, "本地模拟灯：room 客厅/卧室/全部；on/off/brightness/status。亮度为整数0~100。"),
    "lock_control_tool": (LockArgs, "本地模拟门锁：status/lock/unlock。unlock 首次一定要求确认；仅后续用户明确确认才获服务端授权。不能传 confirmed 参数。"),
    "alarm_control_tool": (AlarmArgs, "本地模拟闹钟：set/list/cancel。set 必须用户明确时间，否则询问；time 为未来 ISO8601 +08:00，time_evidence 逐字引用当前指令时间；cancel 无id取消全部。有记录但不后台响铃。"),
    "music_control_tool": (MusicArgs, "本地模拟音乐：play/pause/next/status；不播放真实声音。play 可选 track。"),
    "get_device_status_tool": (StatusArgs, "查询当前会话全部本地模拟设备状态。"),
}


def tool_schemas():
    return [{"type": "function", "function": {
        "name": name, "description": desc, "parameters": schema.model_json_schema(),
    }} for name, (schema, desc) in REGISTRY.items()]


def result(status, message, data=None):
    return {"status": status, "message": message, "data": data or {}, "simulated": True}


def light_control_tool(d: DeviceState, a: LightArgs, **_):
    rooms = list(d.lights) if a.room == "全部" else [a.room]
    for room in rooms:
        light = d.lights[room]
        if a.action == "off":
            light["on"] = False
        elif a.action == "on":
            light["on"] = True
            if light["brightness"] == 0:
                light["brightness"] = 80
        elif a.action == "brightness":
            light.update(on=a.brightness > 0, brightness=a.brightness)
    return result("success", "模拟灯光状态已读取/更新", {r: d.lights[r].copy() for r in rooms})


def lock_control_tool(d: DeviceState, a: LockArgs, *, unlock_authorized=False, **_):
    if a.action == "unlock" and not unlock_authorized:
        return result("confirmation_required", "门锁尚未解锁。请在120秒内点击“确认模拟解锁”，或发送完全相同文字；其他输入会取消本次确认。", {"locked": d.locked})
    if a.action in ("lock", "unlock"):
        d.locked = a.action == "lock"
    return result("success", "模拟门锁状态已读取/更新", {"locked": d.locked})


def alarm_control_tool(d: DeviceState, a: AlarmArgs, *, user_text="", clock=None, **_):
    current = clock or now()
    if a.action == "set":
        if not a.time or not a.time_evidence:
            return result("needs_input", "请明确闹钟日期和时间，例如明天早上8点。")
        # This is a safety/validation guard, never the tool-selection mechanism.
        if a.time_evidence not in user_text or not any(c.isdigit() or c in "一二三四五六七八九十两" for c in a.time_evidence) or not any(c in a.time_evidence for c in ("点", ":", "时")):
            return result("needs_input", "当前指令中缺少可验证的明确时间，请重新指定，例如明天早上8点。")
        try:
            target = datetime.fromisoformat(a.time)
            if target.tzinfo is None or target.utcoffset() != timedelta(hours=8):
                raise ValueError("必须包含北京时间偏移 +08:00")
            if target <= current:
                raise ValueError("闹钟必须为未来时间")
        except ValueError as exc:
            return result("validation_error", f"无效闹钟时间：{exc}")
        if len(d.alarms) >= 20:
            return result("validation_error", "当前会话最多保存20个模拟闹钟，请先取消部分闹钟。")
        for alarm in d.alarms:
            if alarm["time"] == target.isoformat():
                return result("success", "该模拟闹钟已存在，无需重复设置", alarm.copy())
        alarm = {"id": uuid4().hex[:8], "time": target.astimezone(TZ).isoformat()}
        d.alarms.append(alarm)
        return result("success", "已保存模拟闹钟记录（无后台响铃）", alarm.copy())
    if a.action == "list":
        return result("success", "当前模拟闹钟列表", {"alarms": [x.copy() for x in d.alarms]})
    removed = [x for x in d.alarms if a.alarm_id is None or x["id"] == a.alarm_id]
    if not removed:
        return result("not_found", "没有可取消的闹钟", {"cancelled": 0})
    d.alarms[:] = [x for x in d.alarms if x not in removed]
    return result("success", "已取消模拟闹钟", {"cancelled": len(removed)})


def music_control_tool(d: DeviceState, a: MusicArgs, **_):
    playlist = ["轻音乐·晨光", "钢琴·月色", "自然·雨声"]
    if a.action == "play":
        d.music.update(status="playing", track=a.track or d.music["track"] or playlist[0])
    elif a.action == "pause":
        if d.music["track"] is None:
            return result("not_found", "尚无模拟播放记录，无法暂停")
        d.music["status"] = "paused"
    elif a.action == "next":
        previous = d.music["track"]
        i = playlist.index(previous) + 1 if previous in playlist else 0
        d.music.update(status="playing", track=playlist[i % len(playlist)])
    return result("success", "模拟音乐状态已读取/更新（不播放真实音频）", d.music.copy())


def get_device_status_tool(d: DeviceState, a: StatusArgs, **_):
    return result("success", "当前会话全部模拟设备状态", d.snapshot())


HANDLERS = {name: globals()[name] for name in REGISTRY}


def execute_tool(name, arguments, devices, **context):
    if name not in REGISTRY:
        return result("unknown_tool", f"不支持的工具：{str(name)[:80]}")
    try:
        args = REGISTRY[name][0].model_validate(arguments)
        working = copy.deepcopy(devices)
        observation = HANDLERS[name](working, args, **context)
        if observation["status"] == "success":
            devices.lights, devices.locked = working.lights, working.locked
            devices.alarms, devices.music = working.alarms, working.music
        return observation
    except ValidationError as exc:
        errors = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors(include_url=False, include_context=False, include_input=False)]
        return result("validation_error", "工具参数校验失败", {"errors": errors})
    except Exception:
        return result("tool_error", "工具执行异常，未报告成功。请检查设备状态后重试。")
