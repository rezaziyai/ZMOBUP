import time
import requests
from xray_engine import start_xray, stop_xray


def proxy_session(port):
    s = requests.Session(); proxy = f"socks5h://127.0.0.1:{port}"
    s.proxies.update({"http": proxy, "https": proxy}); s.trust_env = False
    return s


def latency(session, url, timeout):
    started = time.perf_counter(); r = session.get(url, timeout=timeout, stream=True); r.close()
    return (time.perf_counter() - started) * 1000


def download_mbps(session, url, timeout, expected_bytes):
    started = time.perf_counter(); received = 0
    with session.get(url, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(131072):
            received += len(chunk)
            if received >= expected_bytes: break
    elapsed = max(time.perf_counter() - started, 0.001)
    return received * 8 / elapsed / 1_000_000


def upload_mbps(session, url, timeout, size):
    payload = b"0" * size; started = time.perf_counter()
    r = session.post(url, data=payload, timeout=timeout); r.close()
    elapsed = max(time.perf_counter() - started, 0.001)
    return size * 8 / elapsed / 1_000_000


def test_config(uri, xray_path, endpoints, settings):
    proc = None; config_path = None
    try:
        proc, port, config_path = start_xray(xray_path, uri); session = proxy_session(port)
        timeout = settings.get("startup_timeout_seconds", 12)
        ping = latency(session, endpoints["latency"], timeout)
        down = download_mbps(session, endpoints["download"], timeout, settings["download_bytes"])
        up = upload_mbps(session, endpoints["upload"], timeout, settings["upload_bytes"])
        score = round((1000 / max(ping, 1)) * 0.2 + down * 0.6 + up * 0.2, 2)
        return {"latency_ms": round(ping, 1), "download_mbps": round(down, 2), "upload_mbps": round(up, 2), "score": score, "status": "ONLINE", "error": ""}
    except Exception as exc:
        return {"latency_ms": None, "download_mbps": None, "upload_mbps": None, "score": 0, "status": "OFFLINE", "error": str(exc)}
    finally:
        if proc: stop_xray(proc, config_path)
