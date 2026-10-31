# 验收用例与测试方法

| 编号 | 用户指令 | 期望工具 | 关键断言 |
|---|---|---|---|
| A | 关闭客厅灯 | light_control_tool | 仅客厅关闭，卧室保持状态 |
| B | 把卧室灯亮度设置为30% | light_control_tool | 卧室on=true，brightness=30 |
| C | 我要睡觉了，关掉灯、锁好门，明早7点叫我 | light + lock + alarm | 全部灯关闭、门锁锁定、明日07:00闹钟 |
| D | 现在家里的设备是什么状态 | get_device_status_tool | 返回完整快照且无修改 |
| E | 设置明天早上8点的闹钟 | alarm_control_tool | 明日08:00+08:00记录 |
| F | 你好 | 无 | 无工具，设备无变化 |
| G | 把门打开 | lock_control_tool | confirmation_required，保持已锁定 |
| G后续 | 确认模拟解锁 | lock_control_tool | 有未过期请求时才解锁；无请求或过期仍拒绝 |
| H有 | 取消闹钟 | alarm_control_tool | 取消全部，cancelled>0 |
| H无 | 取消闹钟 | alarm_control_tool | not_found，不虚报取消成功 |

`tests/test_agent.py`：使用预设 Tool Calls 消息验证图、会话、参数、确认生命周期、上限和失败展示。它不能证明大模型正确理解以上自然语言。

`scripts/evaluate.py --mode live`：使用真实DeepSeek返回的消息，实际执行相同A–H，检查工具集合和设备状态。每个用例使用独立Session；C初始门锁为模拟未锁定以验证“锁门”确实发生；H有预先放置一条模拟闹钟。H分两种所以统计为9条。真实API的自然语言解读与日期计算存在不确定性，失败会写入case.passed=false，脚本以非零退出。

其他覆盖：越界/小数/字符串/布尔亮度、未知房间、虚构工具、非法JSON、额外confirmed注入、缺失/过去/无时区闹钟、闹钟去重、空音乐暂停、会话快照隔离、模型失败、模型汇总失败后实际状态保留、循环上限、批量上限、CSV公式防护、审计持久化、缺Key界面、HTML转义和工具异常原子性。

真实浏览器脚本 `scripts/check_ui.py` 仅用于无Key环境，验证页面、配置失败、两会话对话隔离、JSON下载、清空与重置；截图是真实页面，不是模型成功证据。配置Key后的演示请按demo_script现场操作，再由浏览器真实截图。
