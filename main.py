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
from core.logger import Logger, set_logger
from core.constants import PATHS, REPLAY_MODE
from core.selector import FileSelector
from core.utils import get_conf_value
from core.window import Window


def _prompt_participant_number() -> str:
    while True:
        try:
            participant_number: str = input("Participant number: ").strip()
        except EOFError:
            return "participant_unknown"

        if participant_number:
            return participant_number

        print("Please enter a participant number.")


class OpenMATB:
    def __init__(self) -> None:
        participant_number: str | None = None
        if not REPLAY_MODE:
            participant_number = _prompt_participant_number()

        # The MATB window must be borderless (for non-fullscreen mode)
        Window(style=Window.WINDOW_STYLE_DIALOG, resizable=True)

        if REPLAY_MODE:
            # Skip the selector when a replay session ID is given via command line
            if len(sys.argv) > 2:
                selected: Path | None = None
            else:
                selected = FileSelector(Window.MainWindow, "replay").run()
                if selected is None:
                    sys.exit(0)
            ReplayScheduler(session_path=selected)
        else:
            # Show the scenario selector only if no scenario is set in config.ini
            ini_scenario: str = get_conf_value("Openmatb", "scenario_path").strip()
            if ini_scenario:
                selected = PATHS["SCENARIOS"].joinpath(ini_scenario)
            else:
                selected = FileSelector(Window.MainWindow, "scenario").run()
                if selected is None:
                    sys.exit(0)

            set_logger(Logger(participant_id=participant_number, scenario_path=selected))
            Scheduler(scenario_path=selected)


if __name__ == "__main__":
    app: OpenMATB = OpenMATB()
