#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI选基H5 —— 本地开发代理（零依赖，仅用 Python 标准库）

作用：
  1. 托管当前目录下的静态文件（index.html / fund-pool.js 等）
  2. 提供 POST /ark 接口：把请求原样转发到火山方舟 Ark，
     由服务端发起（不受浏览器 CORS 限制），并补上 CORS 头返回给前端

这样本地打开 http://localhost:8080/ 时，前端会自动走 /ark 代理，AI 真正可用。

用法：
  python3 local-ark-proxy.py                # 默认 8080 端口
  PORT=9000 python3 local-ark-proxy.py      # 自定义端口
  ARK_API_KEY=ark-xxxx python3 local-ark-proxy.py   # 显式指定方舟 Key

Key 来源优先级：环境变量 ARK_API_KEY > 自动从 index.html 的 ARK_KEY_ENCODED 解码
"""
import base64
import json
import os
import socketserver
import urllib.request
from http.server import BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", "8080"))
ARK_URL = "https://ark.cn-beijing.volces.com/api/plan/v3/chat/completions"
SALT = "AI_FUND_SELECT_2026"
# 与 index.html 中的 ARK_KEY_ENCODED 保持一致（前端 XOR+Base64 混淆）
ENCODED = "IDs0azAod2k2ICgmbmFrAlQfAnh8Z2s0fHxnfnV8fHVtPgsIU1V4K3IjbHp9Og=="

ROOT = os.path.dirname(os.path.abspath(__file__))


def decode_key():
    env = os.environ.get("ARK_API_KEY")
    if env:
        return env
    try:
        raw = base64.b64decode(ENCODED)
        return "".join(chr(b ^ ord(SALT[i % len(SALT)])) for i, b in enumerate(raw))
    except Exception:
        return ""


KEY = decode_key()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path != "/ark":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            req = urllib.request.Request(
                ARK_URL,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + KEY,
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                status = resp.status
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            path = "/index.html"
        fp = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
        if not fp.startswith(ROOT) or not os.path.isfile(fp):
            self.send_response(404)
            self.end_headers()
            return
        ext = os.path.splitext(fp)[1].lower()
        ct = CONTENT_TYPES.get(ext, "application/octet-stream")
        with open(fp, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    if not KEY:
        print("[警告] 未能解析到方舟 API Key，请设置环境变量 ARK_API_KEY")
    # ThreadingTCPServer：支持并发，便于局域网内多台设备同时访问；allow_reuse_address 避免端口占用
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True
        allow_reuse_address = True
    with ThreadingHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"本地代理已启动:")
        print(f"  页面:  http://localhost:{PORT}/")
        print(f"  AI接口: http://localhost:{PORT}/ark  (自动转发至火山方舟)")
        print(f"  按 Ctrl+C 退出")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")
