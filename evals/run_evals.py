"""
evals/run_evals.py — Phase 5 evaluation system.

Loads each JSON scenario from evals/scenarios/, runs the full pipeline
(event detection → enrich → plan → mock advice), validates expected fields,
prints a pass/fail table, writes evals/report.md, and exits 1 if any fail.
"""
import json
import os
import sys
import time
from pathlib import Path

# Force mock provider before any backend imports
os.environ["LLM_PROVIDER"] = "mock"

# Add project root to path so backend imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.context.engine import build_context_packet, enrich_summary_with_events
from backend.advice.planner import plan
from backend.llm.advisor import get_mock_advice
from backend.riot.live_client import GameState
from backend.timeline.event_detector import EventDetectorPipeline
from backend.timeline.detectors.cs_drop import CSDropDetector
from backend.timeline.detectors.death_streak import DeathStreakDetector
from backend.timeline.detectors.gold_spike import GoldSpikeDetector
from backend.timeline.detectors.low_health import LowHealthDetector
from backend.timeline.detectors.vision_warning import VisionWarningDetector

_PIPELINE = EventDetectorPipeline(detectors=[
    LowHealthDetector(),
    GoldSpikeDetector(),
    DeathStreakDetector(),
    CSDropDetector(),
    VisionWarningDetector(),
])

_SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
_REPORT_PATH = Path(__file__).resolve().parent / "report.md"


def _build_state(conditions: dict) -> GameState:
    health_percent = conditions["health_percent"]
    return GameState(
        current_health=health_percent / 100 * 2000,
        max_health=2000,
        gold=conditions.get("gold", 1000),
        level=conditions.get("level", 8),
        game_time=conditions["game_time_minutes"] * 60,
        champion_name="Rumble",
        kills=0,
        deaths=conditions.get("deaths", 0),
        assists=0,
        creep_score=conditions.get("creep_score", 60),
        ward_score=conditions.get("ward_score", 3.0),
        assigned_position=conditions.get("assigned_position", "TOP"),
        position=conditions.get("assigned_position", "TOP"),
        ally_champions=("Rumble",),
        enemy_champions=("Tryndamere",),
        all_champions=("Rumble", "Tryndamere"),
    )


def _run_scenario(scenario: dict) -> dict:
    """Run a single scenario and return a result dict."""
    name = scenario["name"]
    conditions = scenario["conditions"]
    expected = scenario["expected"]

    state = _build_state(conditions)
    packet = build_context_packet(state)
    events = _PIPELINE.run(state, packet)
    enriched_packet = enrich_summary_with_events(packet, events)
    advice_request = plan(events, [])

    t0 = time.monotonic()
    advice_text = get_mock_advice(enriched_packet, None, "ko", advice_request)
    latency_ms = int((time.monotonic() - t0) * 1000)

    detected_types = [e.event_type for e in events]

    # Validate each expectation
    failures = []

    # detected_events: scenario must detect AT LEAST these event types
    for expected_event in expected.get("detected_events", []):
        if expected_event not in detected_types:
            failures.append(f"missing event {expected_event} (got {detected_types})")

    # advice_mode
    if "advice_mode" in expected:
        if advice_request.mode != expected["advice_mode"]:
            failures.append(f"mode={advice_request.mode!r} want {expected['advice_mode']!r}")

    # advice_contains
    for phrase in expected.get("advice_contains", []):
        if phrase not in advice_text:
            failures.append(f"advice missing {phrase!r}")

    # advice_contains_not
    for phrase in expected.get("advice_contains_not", []):
        if phrase in advice_text:
            failures.append(f"advice should not contain {phrase!r}")

    # latency
    max_latency = expected.get("max_latency_ms", 2000)
    if latency_ms > max_latency:
        failures.append(f"latency {latency_ms}ms > {max_latency}ms")

    passed = len(failures) == 0
    return {
        "name": name,
        "detected_types": detected_types,
        "mode": advice_request.mode,
        "advice_text": advice_text,
        "latency_ms": latency_ms,
        "passed": passed,
        "failures": failures,
    }


def _check(val: bool) -> str:
    return "✅" if val else "❌"


def main() -> int:
    scenario_files = sorted(_SCENARIOS_DIR.glob("*.json"))
    if not scenario_files:
        print("No scenarios found in evals/scenarios/")
        return 1

    results = []
    for path in scenario_files:
        with open(path) as f:
            scenario = json.load(f)
        result = _run_scenario(scenario)
        results.append(result)

    # Print table
    header = f"{'Scenario':<25} {'Events':<30} {'Mode':<12} {'Contains':<10} {'Latency':<10} {'Result'}"
    print(header)
    print("-" * len(header))

    for r in results:
        events_str = ",".join(r["detected_types"]) if r["detected_types"] else "(none)"
        result_str = "✅ PASS" if r["passed"] else f"❌ FAIL: {'; '.join(r['failures'])}"
        print(f"{r['name']:<25} {events_str:<30} {r['mode']:<12} {'✅' if r['passed'] else '❌':<10} {r['latency_ms']}ms{'':<5} {result_str}")

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_latency = sum(r["latency_ms"] for r in results) // total if total else 0

    print()
    print(f"Summary: {passed_count}/{total} passed — avg latency {avg_latency}ms")

    # Write report.md
    _write_report(results, passed_count, total, avg_latency)

    return 0 if passed_count == total else 1


def _write_report(results: list[dict], passed_count: int, total: int, avg_latency: int) -> None:
    lines = [
        "# RiftBuddy Eval Report",
        "",
        "| Scenario | Events | Mode | Contains | Latency | Result |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        events_str = ",".join(r["detected_types"]) if r["detected_types"] else "(none)"
        contains_check = _check(r["passed"])
        result_str = "✅ PASS" if r["passed"] else f"❌ FAIL"
        lines.append(
            f"| {r['name']} | {events_str} | {r['mode']} "
            f"| {contains_check} | {r['latency_ms']}ms | {result_str} |"
        )
    lines += [
        "",
        "## Summary",
        f"- Passed: {passed_count}/{total}",
        f"- Avg latency: {avg_latency}ms",
    ]
    _REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Report written to {_REPORT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
