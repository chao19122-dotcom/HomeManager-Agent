"""One command: repeat offline checks and regenerate authentic report metrics."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
(ROOT/"results").mkdir(exist_ok=True)
def run(*args):
    subprocess.run([sys.executable,"-X","utf8",*args],cwd=ROOT,check=True)

test=subprocess.run([sys.executable,"-X","utf8","-m","pytest","-q","--junitxml=results/pytest.xml"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
(ROOT/"results/pytest_output.txt").write_text(test.stdout+test.stderr,encoding="utf-8")
print(test.stdout)
if test.returncode:
    raise SystemExit(test.returncode)
run("scripts/collect_environment.py")
run("scripts/evaluate.py","--mode","mock")
if not (ROOT/"results/live_summary.json").exists():
    import json
    (ROOT/"results/live_summary.json").write_text(json.dumps({"mode":"live_api","status":"not_run","reason":"离线检查不发起真实API；请显式运行--mode live","executed":0,"passed":0,"failed":0},ensure_ascii=False,indent=2),encoding="utf-8")
run("scripts/make_diagrams.py")
run("scripts/report_results.py")
