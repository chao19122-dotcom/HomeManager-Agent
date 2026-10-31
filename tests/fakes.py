"""Scripted fixtures ONLY: no intent recognition, no real API, not a demo mode."""
import copy
import json
from uuid import uuid4


def calls(*items):
    return {"role": "assistant", "content": "", "tool_calls": [
        {"id": uuid4().hex, "type": "function", "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}
        for name, args in items]}


def text(value="已根据工具结果完成本地模拟处理。"):
    return {"role": "assistant", "content": value}


class ScriptedModel:
    mode = "mock_scripted"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def complete(self, messages, *, use_tools):
        self.requests.append({"messages": copy.deepcopy(messages), "use_tools": use_tools})
        if not self.responses:
            raise AssertionError("脚本响应已耗尽")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return copy.deepcopy(response)
