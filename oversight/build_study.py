"""Build the participant page from the template and the deterministic trial lists.

Writes two copies with identical study content:
  oversight/study/artifact.html  body-only page for publishing as a claude.ai Artifact
                                 (responses saved to the artifact's db);
  oversight/study/index.html     standalone page for any static host (responses copied out).
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from .study_design import export

HERE = Path(__file__).parent / "study"


def build() -> str:
    data = export(HERE / "trials.json")
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    data["version"] = hashlib.sha256(payload.encode()).hexdigest()[:12]
    page = (HERE / "template.html").read_text(encoding="utf8").replace(
        "/*STUDY_JSON*/null", json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
    (HERE / "artifact.html").write_text(page, encoding="utf8", newline="\n")
    head = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}[hidden]{display:none!important}</style></head><body>'
    (HERE / "index.html").write_text(head + page + "</body></html>", encoding="utf8", newline="\n")
    return data["version"]


if __name__ == "__main__":
    print("study version", build())
