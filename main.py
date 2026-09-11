#! .venv/bin/python3

# Copyright 2023-2026, by Julien Cegarra & Benoît Valéry. All rights reserved.
# Institut National Universitaire Champollion (Albi, France).
# License : CeCILL, version 2.1 (see the LICENSE file)

from __future__ import annotations

import gettext
import sys
from pathlib import Path

# Read and install the specified language iso
# The LOCALE_PATH constant can't be set into constants.py because
# the latter must be translated itself
LOCALE_PATH: Path = Path(".", "locales")

# Only language is accessed manually from the config.ini to avoid circular imports
# (i.e., utils needing translation needing utils and so on)
with open("config.ini", "r") as f:
    language_iso: str = [l for l in f.readlines() if "language=" in l][0].split("=")[-1].strip()
language: gettext.GNUTranslations = gettext.translation("openmatb", LOCALE_PATH, [language_iso])
language.install()


# Only after language installation, import core modules (they must be translated)
from core import ReplayScheduler, Scheduler
from core.logger import Logger, get_logger, set_logger
from core.constants import PATHS, REPLAY_MODE
from core.selector import FileSelector
from core.utils import get_conf_value
from core.window import Window


def _get_config_bool(key: str, default: bool = False) -> bool:
    value: str = get_conf_value("Openmatb", key).strip().lower()
    if value == "":
        return default
    return value in {"1", "true", "yes", "on"}


def _get_scenario_paths() -> list[Path]:
    configured_paths = _get_configured_scenario_paths()
    if configured_paths:
        return configured_paths

    selected = FileSelector(Window.MainWindow, "scenario").run()
    if selected is None:
        sys.exit(0)
    return [selected]


def _get_configured_scenario_paths() -> list[Path]:
    sequence_value: str = get_conf_value("Openmatb", "scenario_sequence").strip()
    if sequence_value:
        return [
            PATHS["SCENARIOS"].joinpath(item.strip())
            for item in sequence_value.split(",")
            if item.strip()
        ]

    ini_scenario: str = get_conf_value("Openmatb", "scenario_path").strip()
    if ini_scenario:
        return [PATHS["SCENARIOS"].joinpath(ini_scenario)]

    return []


def _prompt_participant_number() -> str:
    while True:
        try:
            participant_number: str = input("Participant number: ").strip()
        except EOFError:
            return "participant_unknown"

        if participant_number:
            return participant_number

        print("Please enter a participant number.")


def _get_window_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {"resizable": True}
    dialog_style = getattr(Window, "WINDOW_STYLE_DIALOG", None)
    if sys.platform == "darwin" and dialog_style is not None:
        kwargs["style"] = dialog_style
    return kwargs


class OpenMATB:
    def __init__(self) -> None:
        participant_number: str | None = None
        if not REPLAY_MODE:
            participant_number = _prompt_participant_number()

        # On macOS, keep the dialog-style window. On Windows/Linux, prefer the default
        # window style to avoid platform-specific redraw flicker.
        if REPLAY_MODE:
            Window(**_get_window_kwargs())
            # Skip the selector when a replay session ID is given via command line
            if len(sys.argv) > 2:
                selected: Path | None = None
            else:
                selected = FileSelector(Window.MainWindow, "replay").run()
                if selected is None:
                    sys.exit(0)
            ReplayScheduler(session_path=selected)
        else:
            selected_scenarios = _get_configured_scenario_paths()
            needs_selector = len(selected_scenarios) == 0
            if needs_selector:
                Window(**_get_window_kwargs())
                selected_scenarios = _get_scenario_paths()

            logger_scenario = (
                Path("scenario_sequence")
                if len(selected_scenarios) > 1
                else selected_scenarios[0]
            )
            set_logger(Logger(participant_id=participant_number, scenario_path=logger_scenario))

            gaze_recorder = None
            if _get_config_bool("tobii_calibrate_validate_once", default=False):
                from eyetracker_calibrate_validate import calibrate_validate_and_start_recording

                logger = get_logger()
                gaze_output = logger.path.with_name(f"{logger.path.stem}_tobii_gaze.csv")
                gaze_metadata = {
                    "participant_id": logger.participant_id,
                    "session_id": logger.session_id,
                    "scenario_name": logger.scenario_name,
                    "matb_session_file": logger.path.name,
                }
                gaze_recorder = calibrate_validate_and_start_recording(
                    gaze_output,
                    metadata=gaze_metadata,
                    scenario_time_source=lambda: get_logger().scenario_time,
                )
                logger.log_manual_entry(gaze_recorder.output_file.name, key="gaze_file")

            if not needs_selector:
                Window(**_get_window_kwargs())

            try:
                Scheduler(scenario_paths=selected_scenarios)
            finally:
                if gaze_recorder is not None:
                    gaze_recorder.stop()


if __name__ == "__main__":
    app: OpenMATB = OpenMATB()
