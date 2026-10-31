"""Serve Qwen3-14B behind an OpenAI-compatible vLLM endpoint on Modal.

This is a NEW inference backend, not a reproduction of the frozen Ollama qwen3:14b
(Q4_K_M) runs in results/. It serves bf16 weights, so absolute scores can differ from the
original phases; every oversight/ result records the backend it came from.

One-time setup (your Modal account):
    pip install modal
    modal setup
    modal secret create dnc-vllm-key DNC_API_KEY=<any long random string>
Deploy (prints the URL; stop it with `modal app stop dnc-qwen3-monitor`):
    modal deploy oversight/modal_vllm.py
Then:
    export DNC_BASE_URL=https://<workspace>--dnc-qwen3-monitor-serve.modal.run/v1
    export DNC_API_KEY=<same string>

Cost: one L40S at roughly $2/hour, scaled to zero after 5 idle minutes.
"""
import modal

MODEL = "Qwen/Qwen3-14B"
SERVED_NAME = "qwen3-14b"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.9.2", "huggingface_hub[hf_transfer]==0.33.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
app = modal.App("dnc-qwen3-monitor")


@app.function(
    image=image,
    gpu="L40S",
    scaledown_window=5 * 60,
    timeout=60 * 60,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("dnc-vllm-key")],
)
@modal.concurrent(max_inputs=64)
@modal.web_server(port=8000, startup_timeout=15 * 60)
def serve():
    import os
    import subprocess
    cmd = [
        "vllm", "serve", MODEL,
        "--served-model-name", SERVED_NAME,
        "--host", "0.0.0.0", "--port", "8000",
        "--max-model-len", "8192",
        "--api-key", os.environ["DNC_API_KEY"],
    ]
    subprocess.Popen(cmd)
