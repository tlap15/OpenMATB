# Copyright 2023-2026, by Julien Cegarra & Benoît Valéry. All rights reserved.
# Institut National Universitaire Champollion (Albi, France).
# License : CeCILL, version 2.1 (see the LICENSE file)
import csv
import sys
from pathlib import Path
from typing import Any, Optional

from pyglet import font

from core.constants import CONFIG
from core.constants import PATHS as P


def clamp(x: float, val_min: float, val_max: float) -> float:
    if x < val_min:
        return val_min
    elif x > val_max:
        return val_max
    return x


def get_session_id_from_filename(filename: str) -> int | None:
    parts: list[str] = Path(filename).stem.split("_")

    if len(parts) > 0 and parts[0].isdigit():
        return int(parts[0])

    for part in parts:
        if part.startswith("sid") and part[3:].isdigit():
            return int(part[3:])

    return None


def get_session_id_from_csv(path: Path) -> int | None:
    try:
        with open(path, newline="") as csvfile:
            reader: csv.DictReader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("type") == "session_id":
                    value: str | None = row.get("value")
                    if value is not None and value.isdigit():
                        return int(value)
                    return None
    except (OSError, csv.Error):
        return None

    return None


def get_session_numbers() -> list[int]:
    try:
        session_numbers = [
            session_id
            for s in P["SESSIONS"].glob("**/*.csv")
            for session_id in [get_session_id_from_filename(s.name) or get_session_id_from_csv(s)]
            if session_id is not None
        ]
    except OSError:
        session_numbers = [0]

    return session_numbers if len(session_numbers) > 0 else [0]


def find_the_first_available_session_number() -> int:
    session_numbers: list[int] = get_session_numbers()
    first_avail: Optional[int] = None

    # Take max session number + 1, and find the minimum available number into [1, max+1]
    # If no session has been manually removed, it will be max+1
    if len(session_numbers) == 0:
        first_avail = 1
    else:
        for n in range(1, max(session_numbers) + 1):
            if n not in session_numbers and first_avail is None:
                first_avail = n

    if first_avail is None:
        first_avail = max(session_numbers) + 1

    return first_avail


def find_the_last_session_number() -> int:
    session_numbers: list[int] = get_session_numbers()
    return max(session_numbers)


def has_conf_value(section: str, key: str) -> bool:
    return key in CONFIG


def get_conf_value(section: str, key: str, val_type: Optional[type] = None) -> Any:
    value: str = CONFIG[section][key]

    # Boolean boolean values
    if key in ["fullscreen", "highlight_aoi", "hide_on_pause", "display_session_number"]:
        if value.strip().lower() == "true":
            return True
        elif value.strip().lower() == "false":
            return False
        else:
            raise TypeError(
                _("In config.ini, [%s] parameter must be a boolean (true or false, not %s). Defaulting to False")
                % (key, value)
            )

    # Integer values
    elif key in ["screen_index"]:
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise TypeError(_("In config.ini, [%s] parameter must be an integer (not %s)") % (key, value)) from None
        else:
            return value

    # Float values
    elif key in ["clock_speed"]:
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise TypeError(_("In config.ini, [%s] parameter must be a float (not %s)") % (key, value)) from None
        else:
            return value

    # List values
    elif key in ["top_bounds", "bottom_bounds"]:
        try:
            value = eval(value)
        except (ValueError, TypeError, SyntaxError, NameError):
            raise TypeError(
                _("In config.ini, [%s] parameter must be a list of floats (not %s)") % (key, value)
            ) from None
        else:
            return value

    # String value
    else:
        # Font definition & check
        if key == "font_name":
            if len(value) == 0:
                return
            elif not font.have_font(value):
                raise TypeError(_("In config.ini, the specified font is not available. A default font will be used."))
            else:
                return value

        return value


def get_replay_session_id() -> int:
    if len(sys.argv) > 2:
        return int(sys.argv[2])
    elif has_conf_value("Replay", "replay_session_id"):
        return int(get_conf_value("Replay", "replay_session_id"))
    else:
        return int(find_the_last_session_number())
