# 专家工具说明

统一输出：`{status, message, data, simulated: true}`。输入额外字段会被拒绝；状态包括 success、validation_error、needs_input、confirmation_required、not_found、unknown_tool、tool_error、limit_exceeded。

| 名称 | 功能 | 结构化输入 | 输出data |
|---|---|---|---|
| light_control_tool | 客厅/卧室/全部灯开关、亮度、查询 | room: 客厅/卧室/全部；action: on/off/brightness/status；brightness: 仅设置亮度时必填，整数0~100 | 房间到on、brightness的映射 |
| lock_control_tool | 门锁查看、锁定、模拟解锁 | action: status/lock/unlock；不接受模型传confirmed | locked布尔值；未授权返回confirmation_required |
| alarm_control_tool | 闹钟设置、列表、取消 | action: set/list/cancel；set需time ISO8601 +08:00及time_evidence；cancel可选alarm_id | 新闹钟{id,time}、alarms数组或cancelled数量 |
| music_control_tool | 模拟播放、暂停、下一首、状态 | action: play/pause/next/status；play可选track字符串1~100字 | status: playing/paused/stopped，track |
| get_device_status_tool | 查询全部设备 | 空对象{} | lights、locked、alarms、music完整快照 |

门锁解锁授权由会话的pending_unlock_at和当前输入共同验证，未暴露在工具JSON Schema中。即使模型请求直接解锁也只能得到确认提示。闹钟time_evidence必须逐字存在于当前指令，且包含时间表达；这用于防止完全缺失时间时模型编造参数，不承担自然语言意图识别。自然语言到时间的换算仍由在线模型完成。

所有工具仅修改传入的会话设备，不使用真实设备协议、音乐服务或通知服务。单次工具执行失败不应改变该工具负责的设备，多个工具部分成功时会分别显示结果。
