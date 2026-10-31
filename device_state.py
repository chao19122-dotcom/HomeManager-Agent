"""Session-local simulated devices. No hardware/network operations."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
import copy

TZ = ZoneInfo("Asia/Shanghai")


def now():
    return datetime.now(TZ)


@dataclass
class DeviceState:
    lights: dict = field(default_factory=lambda: {
        "客厅": {"on": True, "brightness": 80},
        "卧室": {"on": True, "brightness": 60},
    })
    locked: bool = True
    alarms: list = field(default_factory=list)
    music: dict = field(default_factory=lambda: {"status": "stopped", "track": None})

    def snapshot(self):
        return copy.deepcopy(asdict(self))


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid4().hex)
    devices: DeviceState = field(default_factory=DeviceState)
    messages: list = field(default_factory=list)
    logs: list = field(default_factory=list)
    pending_unlock_at: datetime | None = None
