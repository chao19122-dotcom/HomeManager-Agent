# HomeManager 智能家居管家 Agent

《基于 LangGraph 与大语言模型的智能家居管家 Agent 设计与实现》课程项目。Python + LangGraph + DeepSeek Tool Calls + Gradio，所有设备均为当前浏览器会话内的本地模拟。

目标仓库：[home-manager-agent](https://gitee.com/huang-jiahengJjh/home-manager-agent)。本文件包用于网页手动上传；源码尚需你在网页提交到 `master`，本地打包不代表远程已上传。

## 安装与启动

如果已经下载并解压源码，先进入包含 `app.py` 的目录，从 `python -m venv .venv` 开始执行；不要求安装Git。网页上传完成后，也可以在 PowerShell 中克隆：

```powershell
git clone https://gitee.com/huang-jiahengJjh/home-manager-agent.git
cd home-manager-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # 仅首次执行，勿覆盖已配置的 .env
notepad .env
# 填写 DEEPSEEK_API_KEY，保存后关闭记事本
.\.venv\Scripts\python.exe app.py
```

打开 http://127.0.0.1:7860 。端口占用时用 `app.py --port 7861`。默认仅本机访问，不自动公网分享。修改 .env 后再次发送即可读取配置；外部环境变量优先于 .env。

建议 Python 3.11~3.13，本机实际验证 Python 3.13.9。若已在 `D:\agent` 配置过环境，直接在该目录执行 `.\.venv\Scripts\python.exe app.py`。完整环境快照在 requirements-lock.txt，针对本次 Windows/Python 3.13 环境；跨平台优先使用 requirements.txt。

当前官方文档模型名采用 `deepseek-flash`，Base URL 为 `https://api.deepseek.com`；如账户支持其他模型，通过 .env 的 DEEPSEEK_MODEL 修改，不在代码中存 Key。客户端显式关闭 thinking，仅传递公开消息和 Tool Calls，不保存 reasoning_content。

**没有 Key 时页面仍可打开，但聊天会明确报告配置缺失，不启用假模型。** 离线自动化测试中的 ScriptedModel 仅为测试夹具，没有关键词路由，不代表真实模型决策通过。

## 使用与边界

- 灯光：客厅/卧室/全部，开关与0~100整数亮度；亮度0表示关闭，再开时恢复80%。关闭保留亮度设定值。
- 门锁：状态/锁定/模拟解锁。首次请求只生成确认提示；120秒内点击“确认模拟解锁”或发送该完整文字。其他输入、清空聊天或重置会取消待确认。授权只能使用一次，模型不能提供 confirmed 绕过校验。这里只模拟锁舌状态，不会物理开门。
- 闹钟：设置/查看/按id或全部取消。使用北京时间，必须未来时间；缺失时间询问用户，不编造。只是记录，**没有后台提醒或响铃任务**。
- 音乐：模拟播放、暂停、下一首、查询；不连接音乐服务，不输出音频。
- 状态查询：完整只读快照。刷新或新会话重新初始化设备；服务重启不恢复设备状态。审计日志会保存到 results/sessions/随机会话id/interactions.json。
- 重置设备会重置模型上下文、保留聊天展示和历史审计；清空对话仅清除展示和模型上下文、取消待确认，设备及审计保留。导出会包含清空前记录。
- Gradio State 逐会话独立，工具不使用全局可变设备对象；操作队列串行执行以避免同一会话并发写入。此课程版会同时串行处理不同用户的请求，适合课堂规模。

## 验证与结果

```powershell
# 不联网：工具 + 图流程 + 异常 + 会话隔离；live 默认跳过
.\.venv\Scripts\python.exe -m pytest -q --junitxml=results/pytest.xml
# 或一键重复离线检查并更新报告统计
.\.venv\Scripts\python.exe scripts/run_checks.py
# 离线 A-H 回放，生成统计和日志（H含有/无闹钟两种情况）
.\.venv\Scripts\python.exe scripts/evaluate.py --mode mock
# 配置Key后：真正在线模型选择工具，需要API额度
.\.venv\Scripts\python.exe scripts/evaluate.py --mode live
# 或在线断言测试
.\.venv\Scripts\python.exe -m pytest tests/test_live.py --live -q
```

results/mock_summary.json、mock_interactions.json 为**预设消息测试**；results/live_summary.json 说明真实联调状态。真实联调结果必须运行后再写入报告。工具成功率=success调用数/全部工具调用数，confirmation_required 和 not_found 属预期受控行为，但不算执行成功；用例通过率另列。

本项目已保存真实 DeepSeek A–H 验收 **9/9 通过**的记录，以及真实浏览器 **6 轮连续交互通过**的记录。上传前另运行包含在线集成测试的完整 pytest，结果见 [publish_tests_output.txt](results/publish_tests_output.txt) 和 [JUnit XML](results/publish_tests.xml)。这些是单次实际实验结果，不保证后续 API 网络、额度或模型行为不变。

[课程实验报告](HomeManager智能家居管家Agent课程实验报告.docx) 包含架构、工具、流程、截图和实验分析，封面个人信息留空。报告制作使用的本机 Word 自动化脚本、原始课程模板及参考报告不属于应用运行依赖，未纳入本文件包。

## 提交文件与本地隐私

仓库只保留经检查的课程样例日志和运行截图。`.env`、个人凭据、虚拟环境、缓存、实际用户会话、下载导出以及 Word 排版临时文件均由 .gitignore 排除。本次手动上传副本已单独检查敏感信息和导入关系，真实结果见 `results/manual_upload_checks.json`。网页上传不会自动应用.gitignore，请仅选择本文件包内文件。

结构化参数错误、未知工具、JSON错误、Key缺失、模型超时/响应失败都有明确状态。最多3轮，每轮最多8个执行工具，避免无界循环。模型失败后保留已成功工具的实际状态，结果不回滚整轮。工具错误的原始异常不会把密钥打印到前端。日志只展示程序生成的公开决策摘要，不包含模型隐藏思维链。时间理解仍依赖模型，正式演示前需运行真实用例校验。

## 项目结构

```text
app.py                  Gradio中文界面与会话回调
agent.py                State / Nodes / Edges、DeepSeek网关、审计导出
tools.py                5个自实现工具、Pydantic结构与验证
device_state.py         会话及模拟设备数据模型
config.py               .env配置与固定时区
requirements.txt        直接依赖版本
requirements-lock.txt   本机完整依赖快照
.env.example            配置模板（无Key）
tests/                  工具、Agent、安全边界、可选在线测试
scripts/                A-H评估、图表生成、真实页面截图
docs/                   设计说明、工具表、Mermaid/PNG、演示与Gitee指南
results/                实际测试输出、环境信息、运行截图与审计
```

详见 [报告素材](docs/report_materials.md)、[演示脚本](docs/demo_script.md)、[工具表](docs/tools.md)、[Gitee上传指南](docs/gitee_guide.md) 和 [结果说明](results/README.md)。

## 官方依据

- [LangGraph Graph API Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart)：本项目使用 StateGraph、add_node、add_edge、add_conditional_edges、compile/invoke。
- [DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)：模型返回函数名和JSON参数，由应用执行工具并回传Observation。
- [DeepSeek 模型配置](https://api-docs.deepseek.com/quick_start/pricing/)：2026-10-31查询，部署时以账户可用模型为准。

## 网页手动上传包检查

上传本目录里的文件和子目录到仓库根目录，不要再套一层“Gitee_手动上传文件”目录。详见 [网页上传步骤](docs/gitee_guide.md)，完整文件及SHA-256清单见 [UPLOAD_MANIFEST.json](UPLOAD_MANIFEST.json)。ZIP仅作备份，仓库中应能直接打开app.py。

本次副本无.env，也没有.git、虚拟环境或缓存。离线检查和本次在线检查分别保存结果；已有publish_tests和live_*文件是此前真实实验记录。新机器仍需创建自己的.env并填写Key。截图脚本属于可选辅助工具，可能需要本机Edge/Chrome或另行安装Playwright Chromium；运行app.py不依赖这些浏览器。
