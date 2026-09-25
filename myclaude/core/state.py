import os
import json
import threading
import time
from collections import deque
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional


class SharedState:
    """主 Agent 全局共享黑板状态"""
    def __init__(self):
        self._lock = threading.RLock()
        self.status = "IDLE"  # IDLE, RUNNING, WAITING_TOOL
        self.goal = ""
        self.step = 0
        self.max_steps = 30
        self.active_tool: Optional[str] = None
        self.active_tool_args: Optional[Dict[str, Any]] = None
        self.active_tool_start_time: Optional[float] = None
        self.recent_logs = deque(maxlen=200)
        self.steering_queue: List[str] = []
        self.interrupt_requested = False

    def set_goal(self, goal: str):
        with self._lock:
            self.goal = goal
            self.step = 0
            self.status = "RUNNING"
            self.recent_logs.clear()
            self.steering_queue.clear()
            self.interrupt_requested = False

    def set_status(self, status: str):
        with self._lock:
            self.status = status

    def set_step(self, step: int, max_steps: int = 30):
        with self._lock:
            self.step = step
            self.max_steps = max_steps

    def set_active_tool(self, name: str, args: Dict[str, Any]):
        with self._lock:
            self.active_tool = name
            self.active_tool_args = args
            self.active_tool_start_time = time.time()
            self.status = "WAITING_TOOL"
            self.append_log(f"⚡ 开始执行工具: {name}")

    def clear_active_tool(self):
        with self._lock:
            self.active_tool = None
            self.active_tool_args = None
            self.active_tool_start_time = None
            self.status = "RUNNING"

    def append_log(self, text: str):
        with self._lock:
            timestamp = time.strftime("%H:%M:%S")
            clean_text = text.rstrip("\r\n")
            if clean_text:
                self.recent_logs.append(f"[{timestamp}] {clean_text}")

    def add_steering(self, message: str):
        with self._lock:
            self.steering_queue.append(message)
            self.append_log(f"📢 [收到侧边栏干预指令]: {message}")

    def pop_all_steering(self) -> List[str]:
        with self._lock:
            messages = list(self.steering_queue)
            self.steering_queue.clear()
            return messages

    def request_interrupt(self):
        with self._lock:
            self.interrupt_requested = True
            self.append_log("⚠️ [侧边栏请求中断当前动作]")

    def check_and_clear_interrupt(self) -> bool:
        with self._lock:
            val = self.interrupt_requested
            self.interrupt_requested = False
            return val

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = 0.0
            if self.active_tool_start_time:
                elapsed = round(time.time() - self.active_tool_start_time, 1)

            return {
                "status": self.status,
                "goal": self.goal,
                "step": self.step,
                "max_steps": self.max_steps,
                "active_tool": self.active_tool,
                "active_tool_args": self.active_tool_args,
                "active_tool_elapsed": elapsed,
                "recent_logs": list(self.recent_logs)[-50:],  # 最近 50 行
                "steering_count": len(self.steering_queue),
                "timestamp": time.time(),
            }


# 全局单例黑板
shared_state = SharedState()


class IPCRequestHandler(BaseHTTPRequestHandler):
    """处理来自 sidecar.py 伴生窗口的 HTTP 请求"""

    def log_message(self, format, *args):
        # 静默底层 HTTP access log，防止打扰主终端控制台
        return

    def do_GET(self):
        if self.path == "/api/status":
            data = shared_state.to_dict()
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            req_data = {}

        if self.path == "/api/steer":
            message = req_data.get("message", "").strip()
            if message:
                shared_state.add_steering(message)
                resp = {"success": True, "message": "干预指令已注入主 Agent 队列"}
            else:
                resp = {"success": False, "error": "消息内容不能为空"}

            payload = json.dumps(resp, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)

        elif self.path == "/api/interrupt":
            shared_state.request_interrupt()
            resp = {"success": True, "message": "已向主 Agent 发出中断请求"}
            payload = json.dumps(resp, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()


class IPCServer:
    """管理在主 Agent 进程中运行的 IPC HTTP 服务"""
    def __init__(self, host: str = "127.0.0.1", start_port: int = 9876):
        self.host = host
        self.port = start_port
        self.server: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> int:
        for p in range(self.port, self.port + 20):
            try:
                self.server = ThreadingHTTPServer((self.host, p), IPCRequestHandler)
                self.port = p
                break
            except OSError:
                continue

        if not self.server:
            raise RuntimeError("无法启动 IPC 服务：未找到可用端口")

        # 将当前端口写入本地标记文件，供 sidecar 自动发现
        port_file = Path.cwd() / ".myclaude_port"
        with open(port_file, "w", encoding="utf-8") as f:
            f.write(str(self.port))

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.port

    def stop(self):
        if self.server:
            self.server.shutdown()
        port_file = Path.cwd() / ".myclaude_port"
        if port_file.exists():
            try:
                port_file.unlink()
            except Exception:
                pass


# 全局 IPC 服务实例
ipc_server = IPCServer()
