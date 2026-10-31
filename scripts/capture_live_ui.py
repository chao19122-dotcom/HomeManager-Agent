"""Real browser + real DeepSeek evidence for the final course report."""
from pathlib import Path
import sys
import json
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from config import ROOT
from device_state import now

folder = ROOT / "results/screenshots"
folder.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    page = browser.new_page(viewport={"width":1600,"height":1080},device_scale_factor=1)
    page.goto("http://127.0.0.1:7860", wait_until="domcontentloaded")
    page.get_by_role("heading",name="HomeManager 智能家居管家 Agent",exact=True).wait_for()
    box = page.get_by_role("textbox",name="向管家下达指令",exact=True)
    def send(command, image=None):
        box.fill(command)
        page.get_by_role("button",name="发送指令",exact=True).click()
        expect(box).to_have_value("",timeout=120000)
        expect(page.get_by_role("textbox",name="本次实际执行路径",exact=True)).to_have_value(__import__('re').compile("结束"))
        if image:
            page.screenshot(path=str(folder/image),full_page=True)
    send("我要睡觉了，关掉灯、锁好门，明早7点叫我", "live_multi_tool.png")
    assert "客厅：关" in page.locator("body").inner_text()
    send("把门打开", "live_unlock_pending.png")
    assert "已锁定" in page.locator(".devices").inner_text()
    expect(page.get_by_role("button",name="确认模拟解锁",exact=True)).to_be_enabled()
    # Use the real confirmation button, not a programmatically fabricated authorization.
    page.get_by_role("button",name="确认模拟解锁",exact=True).click()
    expect(page.locator(".devices")).to_contain_text("已模拟解锁",timeout=120000)
    page.screenshot(path=str(folder/"live_unlock_confirmed.png"),full_page=True)
    send("设置闹钟", "live_alarm_clarification.png")
    send("播放轻音乐")
    send("暂停音乐", "live_music_paused.png")
    page.get_by_role("button",name="保存执行日志",exact=True).click()
    link = page.locator('a[href*="/file="]').first
    link.wait_for(timeout=10000)
    response = page.request.get(link.get_attribute("href"))
    assert response.ok
    records = response.json()
    assert len(records) == 6
    assert all(r["mode"] == "live_api" and r["status"] != "model_error" for r in records)
    assert records[1]["device_state"]["locked"] is True
    assert any(a["status"] == "confirmation_required" for a in records[1]["actions"])
    assert records[2]["device_state"]["locked"] is False
    assert records[3]["device_state"]["alarms"] == records[2]["device_state"]["alarms"]
    assert records[4]["device_state"]["music"]["status"] == "playing"
    assert records[5]["device_state"]["music"]["status"] == "paused"
    (ROOT/"results/live_ui_interactions.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    report = {"mode":"real_browser_live_api","time":now().isoformat(),"passed":True,"interactions":len(records),
              "checks":["多工具联动实际状态","未确认门锁保持锁定","点击确认后模拟解锁","缺时间不新增闹钟","模拟音乐播放与暂停","真实JSON日志下载"],
              "screenshots":["live_multi_tool.png","live_unlock_pending.png","live_unlock_confirmed.png","live_alarm_clarification.png","live_music_paused.png"]}
    (ROOT/"results/live_ui_summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    browser.close()
print(json.dumps(report,ensure_ascii=False,indent=2))
