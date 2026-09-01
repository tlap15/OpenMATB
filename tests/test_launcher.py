from __future__ import annotations

from datetime import datetime
from pathlib import Path

from launcher import build_data_destination_dir, copy_runs_to_data_repo, diff_new_files, get_python_executable, sanitize_path_part


class TestSanitizePathPart:
    def test_preserves_safe_characters(self):
        assert sanitize_path_part("station-1_alpha") == "station-1_alpha"

    def test_replaces_unsafe_characters(self):
        assert sanitize_path_part("station 1 / lab") == "station_1___lab"

    def test_uses_default_when_empty(self):
        assert sanitize_path_part("   ", default="fallback") == "fallback"


class TestGetPythonExecutable:
    def test_prefers_windows_venv_python_when_present(self, tmp_path):
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text("")
        assert get_python_executable(tmp_path) == str(venv_python)

    def test_prefers_unix_venv_python_when_present(self, tmp_path):
        venv_python = tmp_path / ".venv" / "bin" / "python3"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text("")
        assert get_python_executable(tmp_path) == str(venv_python)

    def test_uses_conda_prefix_when_available(self, tmp_path, monkeypatch):
        conda_python = tmp_path / "conda" / "python.exe"
        conda_python.parent.mkdir(parents=True)
        conda_python.write_text("")
        monkeypatch.setenv("CONDA_PREFIX", str(conda_python.parent))
        assert get_python_executable(tmp_path / "app") == str(conda_python)


class TestDiffNewFiles:
    def test_returns_sorted_new_files(self, tmp_path):
        a = (tmp_path / "a.csv").resolve()
        b = (tmp_path / "b.csv").resolve()
        c = (tmp_path / "c.csv").resolve()
        before = {b}
        after = {a, b, c}
        assert diff_new_files(before, after) == [a, c]


class TestBuildDataDestinationDir:
    def test_uses_data_folder_and_date(self, tmp_path):
        result = build_data_destination_dir(tmp_path, now=datetime(2026, 9, 1, 8, 24, 26))
        assert result == tmp_path / "2026-09-01"


class TestCopyRunsToDataRepo:
    def test_copies_files_into_date_folder(self, tmp_path):
        source_dir = tmp_path / "sessions"
        source_dir.mkdir()
        source = source_dir / "p19_train_resman_260901_082426.csv"
        source.write_text("data")

        copied = copy_runs_to_data_repo([source], data_dir=tmp_path / "data", now=datetime(2026, 9, 1))

        assert len(copied) == 1
        assert copied[0].read_text() == "data"
        assert copied[0] == tmp_path / "data" / "2026-09-01" / source.name

    def test_renames_duplicate_destination(self, tmp_path):
        source_dir = tmp_path / "sessions"
        source_dir.mkdir()
        source = source_dir / "p19_train_resman_260901_082426.csv"
        source.write_text("new")

        destination_dir = tmp_path / "data" / "2026-09-01"
        destination_dir.mkdir(parents=True)
        (destination_dir / source.name).write_text("old")

        copied = copy_runs_to_data_repo([source], data_dir=tmp_path / "data", now=datetime(2026, 9, 1))

        assert copied[0].name == "p19_train_resman_260901_082426_dup1.csv"
        assert copied[0].read_text() == "new"
