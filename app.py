import argparse
import base64
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RUNTIME = ROOT / "runtime"


def decode_subscription(text: str) -> str:
    """Decode common Base64 subscription payloads, otherwise return text."""
    raw = text.strip()
    if not raw:
        return ""
    for value in (raw, unquote(raw)):
        compact = re.sub(r"\s+", "", value)
        try:
            padded = compact + "=" * (-len(compact) % 4)
            decoded = base64.b64decode(padded, validate=False).decode("utf-8")
            if any(s in decoded.lower() for s in ("vless://", "vmess://", "trojan://", "ss://")):
                return decoded
        except Exception:
            pass
    return raw


def extract_configs(payload: str) -> list[str]:
    text = decode_subscription(payload)
    return re.findall(r"(?:vless|vmess|trojan|ss)://[^\s]+", text, flags=re.I)


def load_settings() -> dict:
    path = ROOT / "settings.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_parse(payload: str) -> int:
    configs = extract_configs(payload)
    print(f"configs={len(configs)}")
    for index, config in enumerate(configs, 1):
        print(f"{index:04d} {config}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="zmobup", description="ZMOBUP V2Ray/Xray speed tester")
    sub = parser.add_subparsers(dest="command", required=True)
    p_parse = sub.add_parser("parse", help="Parse subscription payload")
    p_parse.add_argument("payload", help="Subscription text/Base64 payload")
    args = parser.parse_args()
    if args.command == "parse":
        return cmd_parse(args.payload)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
