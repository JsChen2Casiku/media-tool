import json
import os
import random
import shutil
import subprocess
import urllib
from pathlib import Path


class CommonUtils(object):
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

        js_path = Path(os.path.dirname(os.path.abspath(__file__)))
        self.x_bogus_js_path = js_path / "x_bogus.js"
        self.a_bogus_js_path = js_path / "a_bogus.js"
        self.runner_js_path = js_path / "sign_runner.js"
        self.node_binary = shutil.which("node") or shutil.which("nodejs")

    def _run_js_function(self, script_path: Path, function_name: str, *args) -> str:
        payload = json.dumps(list(args), ensure_ascii=False)
        if not self.node_binary:
            raise RuntimeError("未检测到 node 或 nodejs 可执行文件，请先安装 Node.js 或使用 Docker Compose 部署。")

        try:
            process = subprocess.run(
                [self.node_binary, str(self.runner_js_path), str(script_path), function_name, payload],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("未检测到 node 或 nodejs 可执行文件，请先安装 Node.js 或使用 Docker Compose 部署。") from exc

        if process.returncode != 0:
            stderr = process.stderr.strip() or process.stdout.strip()
            raise RuntimeError(f"Node 签名执行失败: {stderr}")
        return process.stdout.strip()

    def get_xbogus(self, req_url, user_agent):
        query = urllib.parse.urlparse(req_url).query
        return self._run_js_function(self.x_bogus_js_path, "sign", query, user_agent)

    def get_abogus(self, req_url, user_agent):
        query = urllib.parse.urlparse(req_url).query
        return self._run_js_function(self.a_bogus_js_path, "generate_a_bogus", query, user_agent)

    def get_ms_token(self, randomlength=107):
        random_str = ""
        base_str = "ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789="
        length = len(base_str) - 1
        for _ in range(randomlength):
            random_str += base_str[random.randint(0, length)]
        return random_str
