import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from agents import function_tool
from dotenv import load_dotenv

from .context import run_id_var


# ---------------------------------------------------------------------------
# Paths / configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")

VM_HOST = os.environ["LAB_VM_HOST"]
VM_USER = os.environ["LAB_VM_USER"]
VM_KEY = os.environ["LAB_VM_SSH_KEY"]

LOG_DIR = REPO_ROOT / "logs"
TOOL_LOG = LOG_DIR / "tool_calls.jsonl"

COMMAND_TIMEOUT_SECONDS = 60
MAX_RETURNED_OUTPUT = 20_000


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )
        f.flush()


# ---------------------------------------------------------------------------
# VM tool
# ---------------------------------------------------------------------------

@function_tool
async def vm_shell(command: str) -> str:
    """
    Execute a non-interactive shell command inside the isolated evaluation VM.

    The command runs through SSH as the unprivileged lab user.
    """

    started_at = utc_now()

    # Show the action immediately, before SSH executes it.
    print("\n" + "=" * 80, flush=True)
    print("[ACTION] vm_shell", flush=True)
    print(f"[COMMAND] {command}", flush=True)
    print("=" * 80, flush=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-i",
            VM_KEY,
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            f"{VM_USER}@{VM_HOST}",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    except Exception as exc:
        record = {
            "run_id": run_id_var.get(),
            "timestamp_start": started_at,
            "timestamp_end": utc_now(),
            "tool": "vm_shell",
            "command": command,
            "exit_code": None,
            "timed_out": False,
            "execution_error": repr(exc),
            "stdout": "",
            "stderr": "",
        }

        append_jsonl(TOOL_LOG, record)

        print(f"[EXECUTION ERROR] {exc}", flush=True)
        print("=" * 80 + "\n", flush=True)

        return f"Tool execution failed: {exc}"

    timed_out = False

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        timed_out = True

        proc.kill()
        await proc.wait()

        stdout_bytes = b""
        stderr_bytes = (
            f"Command timed out after "
            f"{COMMAND_TIMEOUT_SECONDS} seconds"
        ).encode()

    stdout = stdout_bytes.decode(
        "utf-8",
        errors="replace",
    )

    stderr = stderr_bytes.decode(
        "utf-8",
        errors="replace",
    )

    # Store complete-ish output in the host-side audit log.
    # The model only receives a bounded amount.
    record = {
        "run_id": run_id_var.get(),
        "timestamp_start": started_at,
        "timestamp_end": utc_now(),
        "tool": "vm_shell",
        "command": command,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }

    append_jsonl(TOOL_LOG, record)

    # -----------------------------------------------------------------------
    # Human-visible terminal output
    # -----------------------------------------------------------------------

    print(f"[EXIT CODE] {proc.returncode}", flush=True)

    if timed_out:
        print("[TIMEOUT] true", flush=True)

    if stdout:
        print("\n[STDOUT]", flush=True)
        print(stdout, end="" if stdout.endswith("\n") else "\n", flush=True)

    if stderr:
        print("\n[STDERR]", flush=True)
        print(stderr, end="" if stderr.endswith("\n") else "\n", flush=True)

    print("=" * 80 + "\n", flush=True)

    # -----------------------------------------------------------------------
    # Tool result returned to the model
    # -----------------------------------------------------------------------

    stdout_for_model = stdout[:MAX_RETURNED_OUTPUT]
    stderr_for_model = stderr[:MAX_RETURNED_OUTPUT]

    return (
        f"exit_code={proc.returncode}\n"
        f"timed_out={timed_out}\n"
        f"\n"
        f"stdout:\n"
        f"{stdout_for_model}\n"
        f"\n"
        f"stderr:\n"
        f"{stderr_for_model}"
    )