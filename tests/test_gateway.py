"""SDK boundary unit test; fake SDK response, explicitly not a network test."""
from types import SimpleNamespace as NS
import pytest
from agent import DeepSeekModel
from config import Settings


def test_gateway_payload_and_reasoning_redaction(monkeypatch):
    import agent
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        msg = NS(content="公开回复", reasoning_content="PRIVATE_HIDDEN_REASONING", tool_calls=[
            NS(id="call_1", function=NS(name="get_device_status_tool", arguments="{}"))])
        return NS(choices=[NS(message=msg, finish_reason="tool_calls")])
    monkeypatch.setattr(agent, "OpenAI", lambda **kw: NS(chat=NS(completions=NS(create=create))))
    model = DeepSeekModel(Settings(api_key="test-unit-fixture-only"))
    output = model.complete([{"role":"user","content":"查询状态"}], use_tools=True)
    assert len(requests[0]["tools"]) == 5
    assert requests[0]["extra_body"] == {"thinking":{"type":"disabled"}}
    assert "PRIVATE_HIDDEN_REASONING" not in str(output)
    assert output["tool_calls"][0]["function"]["name"] == "get_device_status_tool"
    model.complete([],use_tools=False)
    assert "tools" not in requests[-1]
