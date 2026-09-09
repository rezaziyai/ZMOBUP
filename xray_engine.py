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


def _transport(parsed, q):
    network = _first(q, "type", "tcp").lower()
    stream = {"network": network}
    if network == "ws":
        stream["wsSettings"] = {"path": _first(q, "path", "/"), "headers": {}}
        host = _first(q, "host", "")
        if host:
            stream["wsSettings"]["headers"]["Host"] = host
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": _first(q, "serviceName", "")}
    elif network == "http":
        stream["httpSettings"] = {"path": _first(q, "path", "/")}
    return stream


def vless_outbound(uri):
    p = urlparse(uri); q = parse_qs(p.query)
    security = _first(q, "security", "none").lower()
    stream = _transport(p, q)
    if security in ("tls", "reality"):
        stream["security"] = "tls" if security == "tls" else "reality"
        tls = {"serverName": _first(q, "sni", p.hostname or "")}
        if security == "tls": tls["allowInsecure"] = True
        else:
            tls.update({"fingerprint": _first(q, "fp", "chrome"), "publicKey": _first(q, "pbk", ""), "shortId": _first(q, "sid", "")})
        stream["tlsSettings" if security == "tls" else "realitySettings"] = tls
    elif security != "none": raise ValueError(f"security ناشناخته: {security}")
    return {"protocol": "vless", "settings": {"vnext": [{"address": p.hostname, "port": p.port or 443, "users": [{"id": p.username, "encryption": _first(q, 'encryption', 'none'), "flow": _first(q, 'flow', '')}]}]}, "streamSettings": stream}


def vmess_outbound(uri):
    import base64
    raw = uri.split("//", 1)[1]; raw += "=" * (-len(raw) % 4)
    obj = json.loads(base64.urlsafe_b64decode(raw).decode("utf-8"))
    network = obj.get("net", "tcp"); stream = {"network": network}
    if network == "ws": stream["wsSettings"] = {"path": obj.get("path", "/"), "headers": {"Host": obj.get("host", "")}}
    if obj.get("tls") == "tls":
        stream["security"] = "tls"; stream["tlsSettings"] = {"serverName": obj.get("sni") or obj.get("host") or obj.get("add"), "allowInsecure": True}
    return {"protocol": "vmess", "settings": {"vnext": [{"address": obj["add"], "port": int(obj.get("port", 443)), "users": [{"id": obj["id"], "alterId": int(obj.get("aid", 0)), "security": obj.get("scy", "auto")}]}]}, "streamSettings": stream}


def build_config(uri, socks_port):
    scheme = urlparse(uri).scheme.lower()
    if scheme == "vless": outbound = vless_outbound(uri)
    elif scheme == "vmess": outbound = vmess_outbound(uri)
    else: raise ValueError(f"فعلاً تست واقعی {scheme.upper()} پیاده‌سازی نشده است")
    return {"log": {"loglevel": "warning"}, "inbounds": [{"listen": "127.0.0.1", "port": socks_port, "protocol": "socks", "settings": {"auth": "noauth", "udp": True}}], "outbounds": [outbound]}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def start_xray(xray_path, uri):
    port = free_port(); temp = tempfile.NamedTemporaryFile(prefix="zmobup_", suffix=".json", delete=False)
    config_path = temp.name; temp.close()
    Path(config_path).write_text(json.dumps(build_config(uri, port), ensure_ascii=False), encoding="utf-8")
    proc = subprocess.Popen([str(xray_path), "run", "-c", config_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if proc.poll() is not None: break
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25): return proc, port, config_path
        except OSError: time.sleep(0.15)
    stop_xray(proc, config_path); raise RuntimeError("Xray برای این کانفیگ بالا نیامد")


def stop_xray(proc, config_path):
    try:
        if proc and proc.poll() is None: proc.terminate(); proc.wait(timeout=2)
    except Exception:
        try: proc.kill()
        except Exception: pass
    try: os.unlink(config_path)
    except OSError: pass
