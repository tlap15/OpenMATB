from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

APP_REPO: Path = Path(__file__).resolve().parent
DATA_REPO: Path = APP_REPO.parent / "openmatb-data"
DATA_DIR: Path = DATA_REPO / "data"
SESSIONS_DIR: Path = APP_REPO / "sessions"
DEFAULT_BRANCH: str = "main"


def sanitize_path_part(value: str, default: str = "unknown") -> str:
    sanitized = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in value.strip())
    sanitized = sanitized.strip("_")
    return sanitized or default


def get_python_executable(app_repo: Path = APP_REPO) -> str:
    user_home = Path.home()
    conda_prefix = os.environ.get("CONDA_PREFIX")

    candidates: list[Path] = [
        app_repo / ".venv" / "Scripts" / "python.exe",
        app_repo / ".venv" / "bin" / "python3",
        app_repo / ".venv" / "bin" / "python",
    ]

    if conda_prefix:
        candidates.extend(
            [
                Path(conda_prefix) / "python.exe",
                Path(conda_prefix) / "bin" / "python3",
                Path(conda_prefix) / "bin" / "python",
            ]
        )

    candidates.extend(
        [
            user_home / "anaconda3" / "python.exe",
            user_home / "miniconda3" / "python.exe",
            user_home / "Anaconda3" / "python.exe",
            user_home / "Miniconda3" / "python.exe",
            Path("/opt/anaconda3/bin/python3"),
            Path("/opt/miniconda3/bin/python3"),
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run_command(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=check, text=True, capture_output=True)


def scan_session_files(sessions_dir: Path = SESSIONS_DIR) -> set[Path]:
    if not sessions_dir.exists():
        return set()
    return {p.resolve() for p in sessions_dir.glob("**/*.csv") if p.is_file()}


def diff_new_files(before: set[Path], after: set[Path]) -> list[Path]:
    return sorted(after - before)


def build_data_destination_dir(data_dir: Path = DATA_DIR, now: datetime | None = None) -> Path:
    dt = now or datetime.now()
    return data_dir / dt.strftime("%Y-%m-%d")


def copy_runs_to_data_repo(
    run_files: Iterable[Path],
    data_dir: Path = DATA_DIR,
    now: datetime | None = None,
) -> list[Path]:
    destination_dir = build_data_destination_dir(data_dir=data_dir, now=now)
    destination_dir.mkdir(parents=True, exist_ok=True)

    copied_paths: list[Path] = []
    for source in sorted(run_files):
        destination = destination_dir / source.name
        if destination.exists():
            stem = destination.stem
            suffix = destination.suffix
            duplicate_index = 1
            while destination.exists():
                destination = destination_dir / f"{stem}_dup{duplicate_index}{suffix}"
                duplicate_index += 1
        _ = shutil.copy2(source, destination)
        copied_paths.append(destination)
    return copied_paths


def update_app_repo(app_repo: Path = APP_REPO, branch: str = DEFAULT_BRANCH) -> tuple[bool, str]:
    try:
        _ = run_command(["git", "pull", "--rebase", "origin", branch], cwd=app_repo)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return False, f"Warning: could not update OpenMATB before launch ({exc}). Continuing with the local copy."
    return True, "OpenMATB code updated successfully."


def run_openmatb(app_repo: Path = APP_REPO) -> int:
    python_executable = get_python_executable(app_repo)
    completed = subprocess.run([python_executable, "main.py"], cwd=app_repo)
    return completed.returncode


def sync_data_repo(data_repo: Path = DATA_REPO, branch: str = DEFAULT_BRANCH) -> tuple[bool, str]:
    try:
        status = run_command(["git", "status", "--porcelain"], cwd=data_repo)
        if not status.stdout.strip():
            return True, "No data changes needed syncing."

        _ = run_command(["git", "add", "."], cwd=data_repo)
        commit_message = f"Add OpenMATB run data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        _ = run_command(["git", "commit", "-m", commit_message], cwd=data_repo)
        _ = run_command(["git", "push", "origin", branch], cwd=data_repo)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return (
            False,
            f"Run data saved locally in the data repo, but upload failed ({exc}). It will be retried next time.",
        )

    return True, "Run data uploaded successfully."


def ensure_data_repo_ready(data_repo: Path = DATA_REPO) -> None:
    if not data_repo.exists():
        raise FileNotFoundError(f"Data repository not found: {data_repo}")
    if not (data_repo / ".git").exists():
        raise FileNotFoundError(f"Data repository is not a git repository: {data_repo}")


def main() -> int:
    print("=== OpenMATB launcher ===")
    print(f"App repo: {APP_REPO}")
    print(f"Data repo: {DATA_REPO}")
    print(f"Data folder: {DATA_DIR}")

    try:
        ensure_data_repo_ready(DATA_REPO)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    updated, update_message = update_app_repo(APP_REPO)
    print(update_message)
    if not updated:
        print("Proceeding without updating the code.")

    print("Scanning existing session files...")
    before = scan_session_files(SESSIONS_DIR)

    print("Launching OpenMATB...")
    return_code = run_openmatb(APP_REPO)
    if return_code != 0:
        print(f"OpenMATB exited with code {return_code}.")

    print("Scanning session files after the run...")
    after = scan_session_files(SESSIONS_DIR)
    new_files = diff_new_files(before, after)

    if new_files:
        print(f"Detected {len(new_files)} new session file(s).")
        copied = copy_runs_to_data_repo(new_files, DATA_DIR)
        for path in copied:
            print(f"Copied: {path}")
    else:
        print("No new session files were detected.")

    synced, sync_message = sync_data_repo(DATA_REPO)
    print(sync_message)

    if return_code == 0 and synced:
        print("All done: run saved locally and pushed to the data repository.")
    elif return_code == 0:
        print("Run completed and was saved locally, but remote upload is still pending.")

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
