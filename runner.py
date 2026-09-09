import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from speedtest import test_config

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def run_tests(configs, settings, xray_path, endpoints, test_mode="both", on_result=None):
    results = []
    workers = max(1, int(settings.get("parallel", 4)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(test_config, c.uri, xray_path, endpoints, settings, test_mode): c for c in configs}
        for done in as_completed(jobs):
            cfg = jobs[done]; result = done.result()
            result.update({"index": cfg.index, "remark": cfg.remark, "protocol": cfg.protocol, "uri": cfg.uri, "source": getattr(cfg, "source", "")})
            results.append(result)
            if on_result: on_result(result, len(results), len(configs))
    return sorted(results, key=lambda x: x.get("score", 0), reverse=True)


def save_results(results, top_n=20):
    (RESULTS / "latest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["index", "remark", "protocol", "source", "status", "latency_ms", "download_mbps", "upload_mbps", "score", "error"]
    with (RESULTS / "latest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(results)
    top = results[:top_n]
    (RESULTS / "top20.txt").write_text("\n".join(f"{i}. {r['remark']} | {r['protocol']} | {r['score']}" for i, r in enumerate(top, 1)), encoding="utf-8")
    return top
