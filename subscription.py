import base64
import json
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse
import requests

@dataclass
class SubscriptionConfig:
    index: int
    uri: str
    protocol: str
    remark: str

def _b64decode(text):
    raw=text.strip().replace("-","+").replace("_","/"); raw += "="*(-len(raw)%4)
    try:return base64.b64decode(raw).decode("utf-8",errors="replace")
    except Exception:return None

def decode_subscription(body):
    body=body.strip()
    if re.search(r"(?:vless|vmess|trojan|ss)://",body,re.I): return body
    decoded=_b64decode(unquote(body)); return decoded if decoded else body

def extract_configs(payload):
    found=re.findall(r"(?:vless|vmess|trojan|ss)://[^\s\r\n]+",payload,flags=re.I); configs=[]
    for idx,uri in enumerate(found,1):
        uri=uri.strip().rstrip(",;"); parsed=urlparse(uri); protocol=parsed.scheme.lower(); remark=""
        if protocol=="vmess":
            try:
                obj=json.loads(_b64decode(uri.split("//",1)[1]) or "{}"); remark=str(obj.get("ps",""))
            except Exception: pass
        if not remark: remark=unquote(parsed.fragment or "").strip()
        if not remark: remark=f"{protocol.upper()} #{idx}"
        configs.append(SubscriptionConfig(idx,uri,protocol.upper(),remark))
    return configs

def fetch_subscription(url,timeout=15):
    if not url.strip(): raise ValueError("لینک Subscription وارد نشده است.")
    response=requests.get(url.strip(),timeout=timeout,headers={"User-Agent":"ZMOBUP/0.1"}); response.raise_for_status()
    configs=extract_configs(decode_subscription(response.text))
    if not configs: raise ValueError("هیچ کانفیگ V2Ray/Xray قابل شناسایی پیدا نشد.")
    return configs
