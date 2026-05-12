"""Unit tests for proactive_coach — pattern extraction, clustering, and triggers."""
import pytest
from backend.timeline.proactive_coach import (
    extract_death_minutes,
    cluster_danger_windows,
    check_triggers,
    DangerWindow,
)


def test_extract_death_minutes_basic():
    text = "Personal history - Rumble: 6/3/8 KDA. Died at 8:12. Died at 14:30. Died at 28:03."
    result = extract_death_minutes(text)
    assert len(result) == 3
    assert abs(result[0] - (8 + 12 / 60)) < 0.01
    assert abs(result[1] - (14 + 30 / 60)) < 0.01
    assert abs(result[2] - (28 + 3 / 60)) < 0.01


def test_extract_death_minutes_empty():
    assert extract_death_minutes("No deaths here.") == []


def test_cluster_groups_nearby_deaths():
    # 3 deaths around 8 min, 2 deaths around 15 min
    times = [7.8, 8.2, 8.5, 14.9, 15.3]
    windows = cluster_danger_windows(times, cluster_radius=1.5, min_count=2)
    assert len(windows) == 2
    centers = sorted(w.center_minutes for w in windows)
    assert abs(centers[0] - 8.17) < 0.1
    assert abs(centers[1] - 15.1) < 0.1


def test_cluster_skips_singleton():
    # Only one death at 20 min — below min_count=2
    times = [8.0, 8.3, 20.0]
    windows = cluster_danger_windows(times, min_count=2)
    assert len(windows) == 1
    assert abs(windows[0].center_minutes - 8.15) < 0.1


def test_cluster_empty_input():
    assert cluster_danger_windows([]) == []


def test_trigger_fires_in_window():
    windows = [DangerWindow(center_minutes=10.0, count=3)]
    # WARN_BEFORE_MINUTES=1.0 → trigger at 9.0 min = 540s
    fired = check_triggers(game_time_seconds=541, windows=windows)
    assert len(fired) == 1
    assert fired[0].triggered is True


def test_trigger_not_before_window():
    windows = [DangerWindow(center_minutes=10.0, count=3)]
    fired = check_triggers(game_time_seconds=480, windows=windows)  # 8 min — too early
    assert fired == []


def test_trigger_not_after_window():
    windows = [DangerWindow(center_minutes=10.0, count=3)]
    # trigger window is [9.0, 9.5] min = [540, 570]s — 600s is past it
    fired = check_triggers(game_time_seconds=600, windows=windows)
    assert fired == []


def test_trigger_fires_only_once():
    windows = [DangerWindow(center_minutes=10.0, count=3)]
    check_triggers(game_time_seconds=541, windows=windows)
    fired_again = check_triggers(game_time_seconds=542, windows=windows)
    assert fired_again == []
