"""Render documented architecture/workflow to Word-ready PNG, no external service."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = next((str(p) for p in [Path("C:/Windows/Fonts/msyh.ttc"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.exists()), None)


def font(size):
    return ImageFont.truetype(FONT, size) if FONT else ImageFont.load_default()


def arrow(draw, a, b, label="", pos=None):
    draw.line([a, b], fill="#436581", width=5)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    pts = [b, (b[0]-17*math.cos(ang-.5), b[1]-17*math.sin(ang-.5)), (b[0]-17*math.cos(ang+.5), b[1]-17*math.sin(ang+.5))]
    draw.polygon(pts, fill="#436581")
    if label:
        x, y = pos or ((a[0]+b[0])/2+15, (a[1]+b[1])/2-18)
        bbox = draw.textbbox((x,y), label, font=font(25))
        draw.rectangle((bbox[0]-5,bbox[1]-4,bbox[2]+5,bbox[3]+4), fill="white")
        draw.text((x,y), label, font=font(25), fill="#334155")


def box(draw, xy, title, detail="", color="#eef6ff"):
    draw.rounded_rectangle(xy, radius=20, fill=color, outline="#6587a4", width=3)
    cx = (xy[0]+xy[2])/2
    draw.text((cx,xy[1]+20), title, anchor="mt", font=font(32), fill="#16324d")
    for i, line in enumerate(detail.split("\n")):
        draw.text((cx,xy[1]+70+36*i), line, anchor="mt", font=font(26), fill="#334155")


def render_architecture():
    im = Image.new("RGB", (1800,1400), "white"); d=ImageDraw.Draw(im)
    d.text((900,40), "HomeManager 系统架构", anchor="mt", font=font(48), fill="#16324d")
    box(d,(480,150,1320,280),"中文 Gradio 交互界面", "聊天 / 设备面板 / 日志导出")
    box(d,(480,350,1320,510),"独立 Session", "模拟设备 / 消息 / 审计 / 待确认解锁")
    box(d,(480,600,1320,760),"LangGraph StateGraph", "模型决策 → 工具执行 → 状态更新 → 模型汇总")
    box(d,(30,610,420,760),"DeepSeek 在线 API", ".env 配置 / Tool Calls", "#f3eeff")
    box(d,(480,850,1320,1010),"校验与专家工具", "Pydantic / 解锁确认 / 执行上限\n灯光 · 门锁 · 闹钟 · 音乐 · 状态")
    box(d,(480,1100,1320,1260),"本地模拟设备与 Observation", "状态更新 / 结果日志 / JSON与CSV")
    box(d,(1390,850,1760,1040),"审计输出", "公开决策摘要\n不含隐藏思维链", "#eafaef")
    for a,b in [((900,280),(900,350)),((900,510),(900,600)),((900,760),(900,850)),((900,1010),(900,1100)),((480,670),(420,670)),((420,710),(480,710)),((1320,940),(1390,940))]: arrow(d,a,b)
    d.text((900,1320), "全部设备为当前会话本地模拟；不连接真实硬件、不输出真实音频、不后台响铃。", anchor="mt", font=font(28), fill="#475569")
    im.save(ROOT / "docs/architecture.png", dpi=(200,200))


def render_workflow():
    im=Image.new("RGB",(1800,1650),"white"); d=ImageDraw.Draw(im)
    d.text((900,30),"LangGraph State / Nodes / Edges",anchor="mt",font=font(46),fill="#16324d")
    box(d,(490,125,1310,255),"用户输入", "会话隔离 / 北京时间 / 当前确认权限")
    box(d,(490,340,1310,500),"llm_decision", "在线模型返回 Tool Calls 或自然语言回复")
    box(d,(490,620,1310,790),"tool_execution", "逐项参数校验 / 服务端授权 / 串行执行\n每轮最多执行8次工具")
    box(d,(490,910,1310,1070),"state_update", "更新会话本地设备 / 记录实际 Observation")
    box(d,(490,1240,1310,1410),"llm_summary", "LLM汇总；失败由确定性结果保护\n以工具实际结果显示成功、失败或待确认")
    box(d,(490,1500,1310,1620),"最终输出", "回复 / 面板 / 审计日志")
    arrow(d,(900,255),(900,340))
    arrow(d,(900,500),(900,620),"有工具调用",(930,540))
    arrow(d,(900,790),(900,910))
    arrow(d,(900,1070),(900,1240),"需确认 / 错误 / 达到3轮",(930,1130))
    arrow(d,(900,1410),(900,1500))
    d.line([(490,990),(180,990),(180,420)],fill="#436581",width=5); arrow(d,(180,420),(490,420))
    d.text((30,1040),"成功且轮次 < 3\n回到模型决定下一步",font=font(26),fill="#334155")
    d.line([(1310,420),(1590,420),(1590,1320)],fill="#436581",width=5); arrow(d,(1590,1320),(1310,1320))
    d.text((1360,820),"无工具调用\n或模型失败",font=font(26),fill="#334155")
    im.save(ROOT/"docs/workflow.png",dpi=(200,200))


if __name__ == "__main__":
    render_architecture(); render_workflow()
    print("Created docs/architecture.png and docs/workflow.png; Mermaid sources in same folder.")
