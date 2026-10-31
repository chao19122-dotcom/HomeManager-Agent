# Gitee 仓库与后续提交

项目仓库：https://gitee.com/huang-jiahengJjh/home-manager-agent

HTTPS远程地址：https://gitee.com/huang-jiahengJjh/home-manager-agent.git

目标分支为 `master`。首次上传由本次提交任务执行，最终是否成功以远程 `refs/heads/master` 与本地HEAD一致为准；不要以本文件存在作为推送成功证据。

## 后续更新

```powershell
cd D:\agent
git status
.\.venv\Scripts\python.exe -m pytest -q
git add app.py agent.py tools.py README.md tests
.\.venv\Scripts\python.exe scripts/audit_staged.py
git diff --cached --stat
git commit -m "说明本次具体修改"
git push origin master
```

只添加本次确实修改的文件。不要使用force push，不要将Token写入远程URL、源码或命令参数。需要认证时通过本机Git Credential Manager窗口或本机Git密码输入提示操作，不要在聊天中发送凭据。

## 上传内容边界

`.gitignore`默认排除.env、凭据、虚拟环境、缓存、用户会话、日志导出、排版临时文件、原始课程文档与参考报告；仅放行检查过的课程样例结果、截图及最终匿名封面报告。`git add .`也不能代替审查和暂存区扫描。

仓库中的报告个人信息留空；报告内的Gitee地址可在最终提交前按本页填写。其他机器运行请按README克隆并创建自己的.env。
