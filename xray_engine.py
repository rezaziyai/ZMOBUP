import base64
import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def _first(q, key, default=""):
    value = q.get(key, [default])
    return unquote(value[0]) if value else default


def _transport(q):
    network = _first(q, "type", "tcp").lower()
    stream = {"network": network}
    if network == "ws":
        ws = {"path": _first(q, "path", "/"), "headers": {}}
        host = _first(q, "host", "")
        if host: ws["headers"]["Host"] = host
        stream["wsSettings"] = ws
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": _first(q, "serviceName", "")}
    elif network == "http":
        stream["httpSettings"] = {"path": _first(q, "path", "/")}
    return stream


def _tls(stream, q, host):
    security = _first(q, "security", "none").lower()
    if security == "tls":
        tls = {"serverName": _first(q, "sni", host)}
        fp = _first(q, "fp", "")
        if fp: tls["fingerprint"] = fp
        alpn = _first(q, "alpn", "")
        if alpn: tls["alpn"] = [x for x in alpn.split(",") if x]
        stream["security"] = "tls"; stream["tlsSettings"] = tls
    elif security == "reality":
        reality = {"serverName": _first(q, "sni", host), "fingerprint": _first(q, "fp", "chrome"), "publicKey": _first(q, "pbk", ""), "shortId": _first(q, "sid", "")}
        spx = _first(q, "spx", "")
        if spx: reality["spiderX"] = spx
        stream["security"] = "reality"; stream["realitySettings"] = reality
    elif security != "none":
        raise ValueError(f"security ناشناخته: {security}")


def vless_outbound(uri):
    p = urlparse(uri); q = parse_qs(p.query); stream = _transport(q); _tls(stream, q, p.hostname or "")
    user = {"id": p.username, "encryption": _first(q, "encryption", "none")}
    flow = _first(q, "flow", "")
    if flow: user["flow"] = flow
    return {"protocol": "vless", "settings": {"vnext": [{"address": p.hostname, "port": p.port or 443, "users": [user]}]}, "streamSettings": stream}


def vmess_outbound(uri):
    raw = uri.split("//", 1)[1]; raw += "=" * (-len(raw) % 4)
    obj = json.loads(base64.urlsafe_b64decode(raw).decode("utf-8")); network = obj.get("net", "tcp"); stream = {"network": network}
    if network == "ws":
        ws = {"path": obj.get("path", "/"), "headers": {}}
        if obj.get("host"): ws["headers"]["Host"] = obj["host"]
        stream["wsSettings"] = ws
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": obj.get("path", "") or obj.get("serviceName", "")}
    if obj.get("tls") in ("tls", True):
        stream["security"] = "tls"; stream["tlsSettings"] = {"serverName": obj.get("sni") or obj.get("host") or obj.get("add")}
        if obj.get("alpn"): stream["tlsSettings"]["alpn"] = obj["alpn"] if isinstance(obj["alpn"], list) else [obj["alpn"]]
    return {"protocol": "vmess", "settings": {"vnext": [{"address": obj["add"], "port": int(obj.get("port", 443)), "users": [{"id": obj["id"], "alterId": int(obj.get("aid", 0)), "security": obj.get("scy", "auto")}]}]}, "streamSettings": stream}


def shadowsocks_outbound(uri):
    p = urlparse(uri); raw = uri.split("//", 1)[1].split("@", 1)[0]; raw += "=" * (-len(raw) % 4)
    userinfo = base64.urlsafe_b64decode(raw).decode("utf-8"); method, password = userinfo.split(":", 1)
    return {"protocol": "shadowsocks", "settings": {"servers": [{"address": p.hostname, "port": p.port or 443, "method": method, "password": password}]}}


def build_config(uri, socks_port):
    scheme = urlparse(uri).scheme.lower()
    if scheme == "vless": outbound = vless_outbound(uri)
    elif scheme == "vmess": outbound = vmess_outbound(uri)
    elif scheme == "ss": outbound = shadowsocks_outbound(uri)
    else: raise ValueError(f"تست {scheme.upper()} پشتیبانی نمی‌شود")
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": socks_port, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [outbound]}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def start_xray(xray_path, uri):
    port = free_port(); temp = tempfile.NamedTemporaryFile(prefix="zmobup_", suffix=".json", delete=False)
    config_path = temp.name; temp.close()
    Path(config_path).write_text(json.dumps(build_config(uri, port), ensure_ascii=False), encoding="utf-8")
    proc = subprocess.Popen([str(xray_path), "run", "-c", config_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            error = (proc.stderr.read() if proc.stderr else "").strip()
            raise RuntimeError(error or "Xray برای این کانفیگ بالا نیامد")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25): return proc, port, config_path
        except OSError: time.sleep(0.15)
    stop_xray(proc, config_path); raise RuntimeError("Xray برای این کانفیگ در زمان مقرر بالا نیامد")


def stop_xray(proc, config_path):
    try:
        if proc and proc.poll() is None: proc.terminate(); proc.wait(timeout=2)
    except Exception:
        try: proc.kill()
        except Exception: pass
    try:
        if proc and proc.stderr: proc.stderr.close()
    except Exception: pass
    try: os.unlink(config_path)
    except OSError: pass
