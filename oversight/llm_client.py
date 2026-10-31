"""Minimal OpenAI-compatible chat client with a crash-safe, append-only call cache.

Standard library only, like the frozen pilot runners. Each completed call is appended to a
JSONL log keyed by (input hash, sample index), so re-running a script resumes instead of
paying twice, and every reported number can be traced to a logged call.
"""
from __future__ import annotations
import hashlib, json, os, re, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = os.environ.get("DNC_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("DNC_API_KEY", "")
MODEL = os.environ.get("DNC_MODEL", "qwen3-14b")
TIMEOUT = 120
# Results land here; point it elsewhere (e.g. a scratch dir) for mock or trial runs.
RUN_DIR = Path(os.environ.get("DNC_RUN_DIR", Path(__file__).resolve().parents[1] / "results" / "oversight"))
_LOCK = threading.Lock()


def now() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def js(x) -> str: return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def digest(s: str) -> str: return hashlib.sha256(s.encode("utf8")).hexdigest()


def load_cache(log: Path) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    if log.exists():
        for line in log.read_text(encoding="utf8").splitlines():
            try: r = json.loads(line)
            except json.JSONDecodeError: continue
            if r.get("parse_success"): out[(r["input_hash"], r["sample_index"])] = r
    return out


def append(log: Path, rec: dict) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, log.open("a", encoding="utf8", newline="\n") as f:
        f.write(js(rec) + "\n"); f.flush(); os.fsync(f.fileno())


def chat(prompt: str, temperature: float, seed: int, max_tokens: int = 400) -> tuple[str, float]:
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temperature,
            "seed": seed, "max_tokens": max_tokens,
            # Qwen3 thinking off: the monitor must answer from the visible events, and the
            # original frozen runs parsed a single JSON object.
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/chat/completions", data=js(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r: data = json.load(r)
    return data["choices"][0]["message"]["content"], time.monotonic() - t0


def parse_json_object(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except json.JSONDecodeError: return None


def cached_call(log: Path, cache: dict, prompt: str, sample_index: int, temperature: float, meta: dict,
                validate) -> dict:
    """Return the cached record for (prompt, sample_index) or make the call, log it and cache it.
    `validate(parsed) -> bool` decides parse_success; failures are logged and retried next run."""
    key = (digest(prompt), sample_index)
    if key in cache: return cache[key]
    rec = {"input_hash": key[0], "sample_index": sample_index, "temperature": temperature, "base_url": BASE_URL,
           "model": MODEL, "timestamp_utc": now(), "prompt": prompt, **meta}
    try:
        raw, latency = chat(prompt, temperature, seed=424242 + sample_index)
        parsed = parse_json_object(raw)
        rec.update(raw_output=raw, latency_s=round(latency, 3), parsed=parsed,
                   parse_success=bool(parsed is not None and validate(parsed)))
    except Exception as e:  # network/HTTP errors are logged, not fatal; the run can resume
        rec.update(error=repr(e), parse_success=False)
    append(log, rec)
    if rec["parse_success"]: cache[key] = rec
    return rec
