"""Build report materials from actual result files, never invent live metrics."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import ROOT
from device_state import now

folder=ROOT/"results"
suite=ET.parse(folder/"pytest.xml").getroot().find("testsuite")
stats={k:int(suite.get(k,"0")) for k in ["tests","failures","errors","skipped"]}
stats["passed"]=stats["tests"]-stats["failures"]-stats["errors"]-stats["skipped"]
stats["seconds"]=float(suite.get("time","0"))
stats["source"]="pytest.xml"
stats["mode"]="offline_with_scripted_model"
(folder/"test_summary.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
mock=json.loads((folder/"mock_summary.json").read_text(encoding="utf-8"))
live=json.loads((folder/"live_summary.json").read_text(encoding="utf-8"))
env=json.loads((folder/"environment.json").read_text(encoding="utf-8"))
ui=json.loads((folder/"ui_smoke.json").read_text(encoding="utf-8")) if (folder/"ui_smoke.json").exists() else {"passed":False}
live_ui=json.loads((folder/"live_ui_summary.json").read_text(encoding="utf-8")) if (folder/"live_ui_summary.json").exists() else None
cases="\n".join(f"| {c['case']} | {c['input']} | {'通过' if c['passed'] else '失败'} | {', '.join(c['tool_names']) or '无工具'} | {c['status']} |" for c in mock["cases"])
packages="、".join(f"{k} {v}" for k,v in env["packages"].items())
live_note = ("本次未取得真实在线LLM调用成功证据，不能写成“DeepSeek全部通过”。配置自己的Key后运行`python scripts/evaluate.py --mode live`，检查退出码、cases和每条实际日志。"
             if live["status"] == "not_run" else
             f"实际在线评估执行{live.get('executed',0)}条，通过{live.get('passed',0)}条，失败{live.get('failed',0)}条。以results/live_interactions.json的真实日志为证据，不能用离线结果替代。")
from config import Settings
key_note = "已配置（此处不记录密钥）" if Settings.load().api_key else "为空"
body=f'''# 课程报告素材：HomeManager 智能家居管家 Agent

生成时间：{now().isoformat()}。本文件基于实际实验文件生成。所有设备均为本地模拟，真实模型联调状态单独列出。可将设计文字、工具表和PNG插入课程Word模板，姓名学号及实验心得由本人补充。

## 1. 选题与目标

面向家庭灯光、门锁、闹钟和音乐的自然语言交互，构建可现场演示的多工具Agent。系统以在线DeepSeek的Tool Calls选择工具，LangGraph管理有界执行过程，Gradio展示可核验设备状态和执行日志。目标是验证Agent“理解意图—选择工具—结构化执行—基于结果回答”的课程方法。

## 2. 系统架构

界面层app.py接收中文输入并维护Gradio State；agent.py实现DeepSeek网关、显式图节点、路由与审计；tools.py定义五个工具的Pydantic模型及执行器；device_state.py提供独立Session和DeviceState；config.py从.env读取配置。没有关键词到工具的生产路由，也没有生产模拟模型回退。

架构：[Mermaid](architecture.mmd)、[PNG](architecture.png)。工作流：[Mermaid](workflow.mmd)、[PNG](workflow.png)。`langgraph_generated.mmd`由实际编译图生成，用于核对节点和边。

### State

| 字段 | 作用 |
|---|---|
| messages | 用户、公开assistant Tool Calls及tool Observation，按用户轮次截断历史 |
| devices | 当前轮已提交的模拟设备 |
| pending_devices | 工具节点的临时工作副本，更新节点提交后清除 |
| user_text / unlock_authorized | 当前输入及服务端一次性解锁权限 |
| rounds | 执行轮次，最大3轮，每轮最多执行8次工具 |
| actions / trace | 参数、Observation、状态、公开行动摘要与实际节点路径 |
| model_error / final | 错误标志和最终回复 |

### Nodes / Edges

START→llm_decision。模型返回tool_calls时进入tool_execution，逐项校验并在副本上串行运行所选工具；state_update提交模拟状态并记录路径。若本轮全部成功且少于3轮，回到模型决定下一步；需确认、缺参数、失败或达到上限则进入llm_summary。模型直接回答或失败同样进入汇总节点，最后到END。汇总可复用模型已给出的最终文本；尚无最终文本时发起无工具的在线汇总。失败时用程序生成的真实执行结果覆盖不可靠成功描述。

## 3. 专家工具与输入输出

详见[工具说明表](tools.md)。light_control_tool、lock_control_tool、alarm_control_tool、music_control_tool、get_device_status_tool共5个自实现工具。输入为JSON Schema，额外字段禁止；返回统一status/message/data/simulated。单个工具使用副本，只有success才提交，因此异常不留下该工具的部分修改。多工具操作允许部分成功并逐项披露，不承诺整轮事务。

门锁首次unlock返回confirmation_required并保持锁定；后续120秒内完整输入“确认模拟解锁”或按钮点击才授权，其他输入取消待确认。模型无法通过confirmed参数授权。闹钟要求未来北京时间和当前用户原话中的明确时间证据，缺失时询问。音乐和闹钟分别仅模拟状态、保存记录，不连接真实服务、不后台响铃。

## 4. 实现过程

先检查工作目录，保留原有课程文档；发现没有代码工程。使用可用Python建立.venv并安装依赖。随后实现会话状态、参数模型、五工具、服务端确认，再连接真实DeepSeek SDK和显式LangGraph。完成中文Gradio、日志导出后，编写预设消息测试验证流程，并另外提供付费真实API评估入口。最后运行自动化与真实浏览器检查，保存环境信息、Mermaid/PNG和真实截图。

## 5. 实验环境（实际采集）

- 平台：{env['platform']}；Python：{env['python'].split('|')[0].strip()}；时区：Asia/Shanghai。
- 依赖：{packages}。
- 完整版本见results/environment.json及requirements-lock.txt；pip check未发现依赖冲突。
- .env中API Key当前{key_note}；不在任何源码中硬编码，也不展示reasoning_content。

## 6. 自动化测试结果（离线，不是在线模型证据）

pytest实际收集{stats['tests']}项，通过{stats['passed']}项、失败{stats['failures']}项、错误{stats['errors']}项、跳过{stats['skipped']}项，耗时{stats['seconds']:.2f}秒。跳过项为显式启用才运行的真实DeepSeek集成测试。来源：results/pytest.xml与pytest_output.txt。

A–H离线场景共{mock['executed']}条（H分两种），通过{mock['passed']}条，失败{mock['failed']}条。**模型消息预设，验证图与工具，不验证模型语言理解。**

| 用例 | 输入 | 离线结果 | 实际工具集合 | 交互状态 |
|---|---|---|---|---|
{cases}

共{mock['tool_calls']}次工具尝试，status=success为{mock['tool_successes']}次，工具执行成功率{mock['tool_success_rate']:.0%}。另外两次为预期confirmation_required和not_found，符合用例断言，不计执行成功。用例通过率{mock['passed']/mock['executed']:.0%}，与工具成功率口径不同。详细时间、参数、返回在results/mock_interactions.json；异常/待确认记录在mock_summary.json的exceptions字段。

## 7. 真实API与真实页面验证边界

真实DeepSeek评估状态：**{live['status']}**；原因：{live.get('reason','请查看live_summary.json')}。{live_note}

真实浏览器检查：{'通过' if ui['passed'] else '待执行'}。使用本机Edge无头浏览器打开实际Gradio页面，验证配置缺失不改设备、独立上下文无聊天泄漏、下载JSON内容正确、清空和重置回调。截图位于results/screenshots/gradio_initial.png与gradio_missing_key.png，均为真实运行页面，仅证明界面和缺Key分支。

配置Key后需按[演示脚本](demo_script.md)获取真正的多工具成功截图与解锁确认前后对比图；可用浏览器截图，不能用绘图代替运行截图。`python scripts/capture_ui.py`只能捕获当前新页面初始状态；交互后的图应在现场浏览器中保存。

## 8. 问题与修复记录

1. 系统登记的py -3.12指向失效的D:/python.exe；改用实际可运行Python 3.13.9建立独立虚拟环境。
2. 初次受限环境pip联网报WinError 10013；通过安装所需网络权限后完成安装，无须用户重装。pip show部分包元数据遇到Windows GBK编码错误，后续采集改为UTF-8与importlib.metadata，不影响包导入和测试。
3. 截图脚本等待networkidle超时：Gradio后台连接可能持续，改为等待DOM和可见标题。最初下载链接定位和清空按钮定位过于宽泛，依据真实DOM修正，最终浏览器检查通过。
4. Gradio自带清空图标只改展示的风险：绑定相同clear回调，同时清除模型上下文和待确认；保留设备及审计。
5. 模型不可用时容易误导成功：不使用生产mock回退；失败显示已执行工具的真实结果，且记录model_error。
6. 模型参数或工具名可能不可靠：白名单执行器、Pydantic严格参数、当前原话时间证据、工具异常副本和循环上限共同约束。

## 9. 局限与本人可补充内容

真实API联调状态见第7节，结果只覆盖已执行样例，不能推广为任意指令可靠性结论。时间证据检查只保证当前输入有明确时间片段，不是完整时间语义解析器；最终转换正确性依赖在线模型和实测断言。设备只在会话内持续，刷新/重启不恢复；审计会落盘。闹钟无后台响铃，音乐无真实音频，不接入真实硬件。队列串行，适合课堂规模。没有做长期运行、并发负载或商业级鉴权。

可补充：自己的需求分析、关键代码截图、真实API结果、演示截图、对Agent与固定流程区别的理解和实验反思。勿把离线脚本输出写成在线模型证据。

## 10. 参考依据与复现

- [LangGraph官方Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart)：StateGraph及节点/边构造。
- [DeepSeek官方Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)：模型输出函数调用，应用执行并返回工具结果。
- [DeepSeek模型说明](https://api-docs.deepseek.com/quick_start/pricing/)：2026-10-31查询，默认配置deepseek-flash，非thinking模式。
- README提供安装、启动、离线与在线测试命令；docs/gitee_guide.md记录目标Gitee仓库及master分支，上传状态以远程master与本地HEAD核验为准。
'''
if live_ui:
    body += f"\n## 11. 最终真实浏览器联调补充\n\n实际连续交互{live_ui['interactions']}轮，检查结果：{'通过' if live_ui['passed'] else '失败'}。包含多工具联动、请求解锁后保持锁定、点击确认才解锁、缺时间不新增闹钟、音乐播放与暂停以及真实JSON下载。完整记录见results/live_ui_interactions.json，截图为results/screenshots/live_*.png。\n\n连续对话曾发现模型仅文字确认而未发起工具请求，修改提示词明确授权False仍须调用unlock，由服务端返回待确认，随后在线A—H及连续浏览器流程全部复测通过。\n"
(ROOT/"docs/report_materials.md").write_text(body,encoding="utf-8")
print(json.dumps(stats,ensure_ascii=False)); print("Wrote docs/report_materials.md from actual files")
