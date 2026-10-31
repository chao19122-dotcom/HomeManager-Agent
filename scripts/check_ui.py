"""Real browser smoke test with no fabricated LLM responses."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from device_state import now
from config import ROOT, Settings

folder = ROOT / "results/screenshots"
folder.mkdir(parents=True,exist_ok=True)
assert not Settings.load().api_key, "本脚本仅测试缺Key分支；已配置时使用真实API评估并手工截图。"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    a, b = browser.new_context(viewport={"width":1600,"height":1080}), browser.new_context(viewport={"width":1600,"height":1080})
    page, other = a.new_page(), b.new_page()
    for tab in (page, other):
        tab.goto("http://127.0.0.1:7860", wait_until="domcontentloaded")
        tab.get_by_role("heading",name="HomeManager 智能家居管家 Agent",exact=True).wait_for()
    page.screenshot(path=str(folder/"gradio_initial.png"), full_page=True)
    page.get_by_role("textbox",name="向管家下达指令",exact=True).fill("关闭客厅灯")
    page.get_by_role("button",name="发送指令",exact=True).click()
    page.get_by_text("缺少 DEEPSEEK_API_KEY，请在项目 .env 中配置；当前不会降级为模拟模型。",exact=True).first.wait_for()
    assert other.get_by_text("关闭客厅灯",exact=True).count() <= 1  # Its only copy is in the examples.
    assert "缺少 DEEPSEEK_API_KEY，请在项目 .env" not in other.locator("body").inner_text()
    assert "客厅：开 / 80%" in page.locator("body").inner_text()
    page.screenshot(path=str(folder/"gradio_missing_key.png"),full_page=True)
    page.get_by_role("button", name="保存执行日志", exact=True).click()
    download = page.locator('a[href*="/file="]').first
    try:
        download.wait_for(timeout=10000)
        response = page.request.get(download.get_attribute("href"))
        assert response.ok
        assert json.loads(response.text())[0]["user_input"] == "关闭客厅灯"
    except Exception:
        print(page.locator("body").inner_text()[-5000:])
        print(page.locator("a").evaluate_all("els => els.map(e => ({text:e.innerText,href:e.getAttribute('href')}))"))
        page.screenshot(path=str(folder/"export_debug.png"), full_page=True)
        raise
    page.get_by_role("button", name="清空对话", exact=True).last.click()
    from playwright.sync_api import expect
    expect(page.get_by_role("textbox",name="本次实际执行路径",exact=True)).to_have_value("对话已清空；模拟设备和历史审计日志保留")
    page.get_by_role("button", name="重置模拟设备状态", exact=True).click()
    expect(page.get_by_role("textbox",name="本次实际执行路径",exact=True)).to_have_value("界面重置 → 初始模拟状态")
    report = {"time": now().isoformat(),"mode":"real_browser_no_api_key", "passed":True,
              "checks":["真实Gradio页面加载","缺Key明确报错且不改变设备","两个浏览器会话无聊天泄漏","JSON日志下载组件生成","清空和重置按钮可调用"],
              "screenshots":["gradio_initial.png","gradio_missing_key.png"],
              "note":"只验证真实页面和配置失败分支，不代表在线LLM联调成功"}
    (ROOT/"results/ui_smoke.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    browser.close()
print(json.dumps(report,ensure_ascii=False,indent=2))
