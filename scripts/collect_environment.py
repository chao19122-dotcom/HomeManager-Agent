from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from device_state import now
from config import ROOT

packages = ["langgraph", "langchain-core", "openai", "gradio", "pydantic", "python-dotenv", "pytest", "pillow", "tzdata", "playwright"]
data = {"collected_at": now().isoformat(), "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "timezone": "Asia/Shanghai",
        "packages": {p: version(p) for p in packages}}
(ROOT/"results").mkdir(exist_ok=True)
(ROOT/"results/environment.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
frozen = subprocess.check_output([sys.executable,"-m","pip","freeze"],text=True)
(ROOT/"requirements-lock.txt").write_text(frozen,encoding="utf-8")
(ROOT/"requirements.txt").write_text("\n".join(f"{p}=={version(p)}" for p in packages)+"\n",encoding="utf-8")
print(json.dumps(data,ensure_ascii=False,indent=2))
