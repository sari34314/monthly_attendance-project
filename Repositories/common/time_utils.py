from datetime import time


def minutes(t: time) -> int:
    """Convert a time to minutes since midnight."""
    return t.hour * 60 + t.minute


def to_time(total_minutes: int) -> time:
    """Convert minutes since midnight back to a time."""
    return time(total_minutes // 60, total_minutes % 60)


def shift_time(t: time, delta_minutes: int) -> time:
    """Move a time by delta minutes, staying inside the same day."""
    shifted = min(max(minutes(t) + delta_minutes, 0), 24 * 60 - 1)
    return to_time(shifted)