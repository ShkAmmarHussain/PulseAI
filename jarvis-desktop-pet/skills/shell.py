import subprocess

CREATE_NO_WINDOW = 0x08000000


def run_command(cmd: str, timeout: int = 30) -> str:
    c = (cmd or "").strip()
    if not c:
        return "Failed: no command specified."
    try:
        r = subprocess.run(
            ["cmd", "/c", c],
            capture_output=True, text=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s: {c}"
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if out:
        return out[:1500]
    if err:
        return f"stderr: {err[:800]}"
    return f"Command finished with exit code {r.returncode} (no output)."
