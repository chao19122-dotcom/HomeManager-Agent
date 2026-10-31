# 实验结果来源

- `pytest_output.txt` / `pytest.xml`：实际执行的自动化测试结果，默认真实API测试跳过。
- `mock_summary.json` / `mock_interactions.json` / `mock_exports/`：预设模型消息驱动的A–H执行；验证工具、流程和状态，**不证明在线模型理解能力**。
- `live_summary.json`：在线评估状态；缺Key时为not_run。配置真实Key并显式运行 `scripts/evaluate.py --mode live` 才会进行付费联调并生成live_interactions.json。
- `environment.json`：实际Python、平台和依赖版本。
- `test_summary.json`：从pytest.xml读取的测试通过/失败/跳过计数；`ui_smoke.json`为真实浏览器检查结果。
- `screenshots/`：仅实际本地Gradio页面截图；缺Key页面仅证明界面可启动，不能证明在线LLM成功。
- `live_ui_summary.json` / `live_ui_interactions.json`：真实在线连续浏览器交互结果，含确认按钮、缺时间询问、音乐播放和暂停；`screenshots/live_*.png`为对应真实截图。
- `sessions/`、`exports/`：用户在界面上的会话审计和下载；可能含个人输入，请勿直接公开。

统计口径：测试通过数量以pytest.xml为准；A–H含H两种情况共9条。工具成功率只计status=success；需要确认和不存在闹钟是预期分支，但不是执行成功。异常记录保留其真实状态。
