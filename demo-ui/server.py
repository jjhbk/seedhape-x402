import asyncio
import json
import os
import re
from pathlib import Path
from typing import AsyncGenerator

from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse

ROOT = Path(__file__).resolve().parent
AGENT_DIR = ROOT.parent / "agent"
INDEX_HTML = ROOT / "index.html"

app = FastAPI(title="Seedhape x402 Demo UI")


def _sse(event: str, data: str) -> str:
    safe = data.replace("\r", "")
    return f"event: {event}\ndata: {safe}\n\n"


def _load_agent_env() -> dict[str, str]:
    env = os.environ.copy()
    env_file = AGENT_DIR / ".env"
    if env_file.exists():
        for key, value in dotenv_values(env_file).items():
            if key and value is not None:
                env[key] = value
    return env


def _extract_tx_link(text: str) -> str | None:
    match = re.search(r"https://sepolia\.basescan\.org/tx/[A-Za-z0-9x]+", text)
    return match.group(0) if match else None


@app.get("/")
def home() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/stream")
async def stream(prompt: str = Query(..., min_length=3)) -> StreamingResponse:
    async def event_gen() -> AsyncGenerator[str, None]:
        env = _load_agent_env()
        cmd = ["python", "-u", "buy.py", prompt]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(AGENT_DIR),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert proc.stdout is not None

        yield _sse("agent", f"USER REQUEST: {prompt}")

        try:
            while True:
                line_b = await proc.stdout.readline()
                if not line_b:
                    break
                line = line_b.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                if line.startswith("THINKING:"):
                    yield _sse("agent", line.replace("THINKING:", "").strip())
                    continue

                if line.startswith("TOOL CALL:"):
                    yield _sse("tool", line)
                    continue

                if line.startswith("RESULT:"):
                    payload = line.replace("RESULT:", "").strip()
                    tx = _extract_tx_link(payload)
                    if tx:
                        yield _sse("tx", f"Settlement visible: {tx}")
                    if "webhook_delivered" in payload:
                        yield _sse("wa", "Seedhape webhook sent to merchant flow")
                    yield _sse("tx", payload)
                    continue

                if line.startswith("ERROR:"):
                    yield _sse("tx", f"ERROR: {line.replace('ERROR:', '').strip()}")
                    continue

                tx = _extract_tx_link(line)
                if tx:
                    yield _sse("tx", f"Settlement visible: {tx}")

                yield _sse("agent", line)

            code = await proc.wait()
            if code == 0:
                yield _sse("done", "complete")
            else:
                yield _sse("tx", f"Agent exited with code {code}")
                yield _sse("done", "failed")
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
