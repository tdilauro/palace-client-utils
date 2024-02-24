from __future__ import annotations

import datetime


def seconds_to_hms(seconds: int) -> str:
    """Converts the given number of seconds to a string of format HH:MM:SS."""
    return str(datetime.timedelta(seconds=seconds))
