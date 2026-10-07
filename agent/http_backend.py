"""Small authenticated HTTP facade around the existing one-shot AgentLoop CLI."""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route


def _build_path(build_file: str) -> Path:
    root = Path(os.environ.get("POB_BUILDS_DIR", "/builds")).resolve()
    candidate = (root / build_file).resolve()
    if not candidate.is_relative_to(root) or candidate.suffix.casefold() != ".xml" or not candidate.is_file():
        raise HTTPException(status_code=400, detail="build_file must name an existing XML file in /builds")
    return candidate


def _authorize(request: Request):
    expected = os.environ.get("POB_AGENT_API_TOKEN", "")
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if not expected or scheme.casefold() != "bearer" or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid bearer token")


def _execute(build: Path, question: str):
    cache = os.environ.get("POB_AGENT_CACHE_DIR", "/data/cache")
    command = [sys.executable, "-m", "agent.cli", "--build", str(build), "--cache-root", cache,
               "--once", "--json", "--no-stream", question]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=300,
                                   cwd=Path(__file__).resolve().parents[1], check=False)
    except subprocess.TimeoutExpired as error:
        raise HTTPException(status_code=504, detail="agent run timed out") from error
    output = completed.stdout.strip().splitlines()
    if not output:
        raise HTTPException(status_code=502, detail=completed.stderr[-2000:] or "agent returned no response")
    try:
        return json.loads(output[-1])
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="agent returned invalid JSON") from error


def _sse_event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _stream_execute(build: Path, question: str):
    cache = os.environ.get("POB_AGENT_CACHE_DIR", "/data/cache")
    command = [sys.executable, "-m", "agent.cli", "--build", str(build), "--cache-root", cache,
               "--once", "--stream-json", question]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   text=True, encoding="utf-8", errors="replace", bufsize=1,
                                   cwd=Path(__file__).resolve().parents[1])
    except OSError:
        yield _sse_event("error", {"message": "agent process could not be started"})
        yield _sse_event("complete", {"status": "error"})
        return

    output = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                output.put(line)
        finally:
            output.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    started = time.monotonic()
    streamed = False
    result = None
    reader_finished = False
    timed_out = False
    try:
        while not reader_finished:
            if time.monotonic() - started > 300:
                timed_out = True
                process.kill()
                yield _sse_event("error", {"message": "agent run timed out"})
                break
            try:
                line = output.get(timeout=0.5)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if line is None:
                reader_finished = True
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                yield _sse_event("error", {"message": "agent returned invalid stream data"})
                continue
            if event.get("type") == "token" and isinstance(event.get("text"), str):
                streamed = True
                yield _sse_event("token", {"text": event["text"]})
            elif event.get("type") == "result" and isinstance(event.get("result"), dict):
                result = event["result"]

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if result is None:
            if not timed_out:
                yield _sse_event("error", {"message": "agent ended without a final response"})
            yield _sse_event("complete", {"status": "error"})
            return

        answer = result.get("answer")
        if isinstance(answer, str) and answer and not streamed:
            yield _sse_event("token", {"text": answer})
        error = result.get("error")
        if not answer and isinstance(error, dict):
            yield _sse_event("error", {"message": error.get("message") or error.get("code") or "agent request failed"})
        yield _sse_event("complete", {"status": result.get("status", "unknown")})
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


async def health(_request):
    return JSONResponse({"status": "ok"})


async def run_agent(request: Request):
    _authorize(request)
    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="request body must be JSON") from error
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="request body must be an object")
    build_file, question = body.get("build_file"), body.get("question")
    if not isinstance(build_file, str) or not build_file.strip() or len(build_file) > 512:
        raise HTTPException(status_code=422, detail="build_file must be a non-empty path within /builds")
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        raise HTTPException(status_code=422, detail="question must contain 1 to 4000 characters")
    build = _build_path(build_file)
    if "text/event-stream" in request.headers.get("accept", "").casefold():
        return StreamingResponse(_stream_execute(build, question), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    return JSONResponse(await run_in_threadpool(_execute, build, question))


app = Starlette(routes=[
    Route("/healthz", health, methods=["GET"]),
    Route("/v1/run", run_agent, methods=["POST"]),
])
