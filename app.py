"""Gradio classroom UI. Start: .venv/Scripts/python app.py"""
import argparse
import html
import json
import gradio as gr
from agent import HomeAgent, DeepSeekModel, export_logs
from config import Settings, ROOT
from device_state import Session, DeviceState, now


def status_panel(session):
    d = session.devices
    lights = " · ".join(f"{r}：{'开' if s['on'] else '关'} / {s['brightness']}%" for r, s in d.lights.items())
    alarms = "<br>".join(html.escape(f"{a['time']} · {a['id']}") for a in d.alarms) or "暂无闹钟"
    music = {"stopped": "未播放", "playing": "模拟播放中", "paused": "已暂停"}[d.music['status']]
    items = [("灯光", lights), ("门锁", "已锁定" if d.locked else "已模拟解锁"),
             ("闹钟", alarms), ("音乐", f"{music} · {html.escape(d.music['track'] or '暂无曲目')}")]
    return '<div class="devices">' + ''.join(
        f'<div class="device"><strong>{title}</strong><p>{value}</p></div>' for title, value in items) + '</div>'


def log_table(session):
    rows = []
    for r in session.logs[-30:]:
        for a in r["actions"] or [{}]:
            rows.append([r["started_at"][11:19], a.get("tool_name", "—"),
                         json.dumps(a.get("arguments", {}), ensure_ascii=False),
                         a.get("status", r["status"]), a.get("observation", {}).get("message", r["decision_summary"])])
    return rows


def send(text, history, session):
    session = session or Session()
    history = list(history or [])
    if not text or not text.strip():
        return "", history, session, status_panel(session), "等待输入", log_table(session), session.logs, gr.update(interactive=bool(session.pending_unlock_at))
    try:
        # No mock option in the production UI; missing credentials cannot masquerade as LLM.
        settings = Settings.load()
        record = HomeAgent(DeepSeekModel(settings), settings).run(session, text)
        reply = record["reply"]
        flow = " → ".join(record["trace"])
    except ValueError as exc:
        reply, flow = str(exc), "配置/输入校验 → 停止（未调用模型和设备工具）"
        record_failure(session, text, reply, flow)
    except Exception:
        reply, flow = "系统执行异常，请检查终端日志并重试。设备实际状态以面板为准。", "异常 → 停止"
        record_failure(session, text, reply, flow)
    history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": reply}])
    return "", history, session, status_panel(session), flow, log_table(session), session.logs, gr.update(interactive=bool(session.pending_unlock_at))


def record_failure(session, text, reply, flow):
    session.pending_unlock_at = None
    session.logs.append({"interaction_id": now().isoformat(), "session_id": session.session_id,
                         "started_at": now().isoformat(), "ended_at": now().isoformat(),
                         "user_input": text, "mode": "not_called", "status": "error",
                         "decision_summary": reply, "actions": [], "trace": [flow], "reply": reply,
                         "device_state": session.devices.snapshot()})
    # Reuse persistence without creating a model/API client.
    audit = ROOT / "results" / "sessions" / session.session_id
    try:
        audit.mkdir(parents=True, exist_ok=True)
        (audit / "interactions.json").write_text(json.dumps(session.logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        session.logs[-1]["audit_warning"] = "日志磁盘保存失败，仍可导出内存记录"


def reset_devices(session):
    session = session or Session()
    session.devices, session.messages, session.pending_unlock_at = DeviceState(), [], None
    record_failure(session, "[界面操作] 重置模拟设备", "设备已重置；模型上下文已重置，聊天展示保留。", "界面重置 → 初始模拟状态")
    session.logs[-1].update(status="ui_reset", mode="ui")
    try:
        path = ROOT / "results" / "sessions" / session.session_id / "interactions.json"
        path.write_text(json.dumps(session.logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        session.logs[-1]["audit_warning"] = "日志磁盘保存失败，仍可导出内存记录"
    return session, status_panel(session), "界面重置 → 初始模拟状态", log_table(session), session.logs, gr.update(interactive=False)


def clear_chat(session):
    session = session or Session()
    session.messages, session.pending_unlock_at = [], None
    return [], session, "对话已清空；模拟设备和历史审计日志保留", gr.update(interactive=False)


CSS = """
.gradio-container {max-width: 1500px !important; font-size: 17px !important;}
.devices {display:grid; gap:12px; margin-top:12px;}
.device {padding:16px 20px; border:1px solid #cbd5e1; border-radius:12px; background:var(--background-fill-secondary);}
.device strong {font-size:21px;} .device p {margin:7px 0 0; font-size:18px; overflow-wrap:anywhere;}
"""


def build_app():
    with gr.Blocks(title="HomeManager 智能家居管家 Agent") as demo:
        session = gr.State(value=lambda: Session())
        gr.Markdown("# HomeManager 智能家居管家 Agent\n自然语言 → DeepSeek 工具决策 → LangGraph 执行 → 可验证结果")
        settings = Settings.load()
        gr.Markdown(f"**全部设备为本地模拟** · 闹钟仅保存记录 · 音乐不输出音频 · {'API Key 已配置（连接尚需验证）' if settings.api_key else '尚未配置 DeepSeek API Key，请先填写 .env'}")
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(label="管家对话", height=390, buttons=["copy_all"])
                text = gr.Textbox(label="向管家下达指令", placeholder="我要睡觉了，关掉灯、锁好门，明早7点叫我", max_lines=3)
                with gr.Row():
                    submit = gr.Button("发送指令", variant="primary")
                    confirm = gr.Button("确认模拟解锁", interactive=False)
                gr.Examples(examples=[[x] for x in ["关闭客厅灯", "把卧室灯亮度设置为30%", "我要睡觉了，关掉灯、锁好门，明早7点叫我", "现在家里的设备是什么状态", "设置明天早上8点的闹钟", "你好", "把门打开", "取消闹钟", "播放轻音乐", "暂停音乐"]], inputs=text)
            with gr.Column(scale=2):
                gr.Markdown("## 当前会话 · 模拟设备")
                status = gr.HTML(status_panel(Session()))
                reset = gr.Button("重置模拟设备状态")
                clear = gr.Button("清空对话")
        gr.Markdown("## LangGraph 执行流程与工具日志")
        flow = gr.Textbox(label="本次实际执行路径", value="等待输入 → LLM决策 → 工具执行 → 状态更新 → LLM汇总", interactive=False)
        table = gr.Dataframe(headers=["北京时间", "Action / 工具", "结构化参数", "执行状态", "Observation / 结果"], datatype=["str"] * 5, interactive=False, wrap=True)
        with gr.Accordion("完整结构化日志（公开行动说明，不含隐藏思维链）", open=False):
            logs = gr.JSON(value=[], label="当前会话交互记录")
        with gr.Row():
            fmt = gr.Radio(["json", "csv"], value="json", label="导出格式")
            export = gr.Button("保存执行日志")
            download = gr.File(label="下载当前会话日志", interactive=False)
        inputs, outputs = [text, chat, session], [text, chat, session, status, flow, table, logs, confirm]
        submit.click(send, inputs, outputs, concurrency_id="session_actions", concurrency_limit=1)
        text.submit(send, inputs, outputs, concurrency_id="session_actions", concurrency_limit=1)
        confirm.click(lambda h, s: send("确认模拟解锁", h, s), [chat, session], outputs, concurrency_id="session_actions", concurrency_limit=1)
        reset.click(reset_devices, session, [session, status, flow, table, logs, confirm], concurrency_id="session_actions", concurrency_limit=1)
        clear.click(clear_chat, session, [chat, session, flow, confirm], concurrency_id="session_actions", concurrency_limit=1)
        # Gradio's built-in clear icon must also clear model context and pending confirmation.
        chat.clear(clear_chat, session, [chat, session, flow, confirm], concurrency_id="session_actions", concurrency_limit=1)
        export.click(lambda s, f: export_logs(s, ROOT / "results" / "exports", f), [session, fmt], download, concurrency_id="session_actions", concurrency_limit=1)
        demo.load(lambda s: status_panel(s), session, status)
    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    build_app().queue(max_size=20).launch(server_name="127.0.0.1", server_port=args.port,
                                         share=False, inbrowser=False, css=CSS)
