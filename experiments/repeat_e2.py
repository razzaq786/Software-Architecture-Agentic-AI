"""
E2 Repeatability Experiment
============================

Runs the complete E2 evaluation repeatedly to test whether the observed
system/scenario outcomes are reproducible.

Design:
    11 scenarios
    x 6 systems
    x 10 repetitions
    = 660 controlled executions

This is a repeatability experiment, NOT a statistical significance test.

Outputs:
    results/e2/e2_repetitions.csv
    results/e2/e2_repetition_summary.csv
    results/e2/e2_repeatability_check.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------
# Reuse the existing E2 evaluator definitions
# ---------------------------------------------------------------------

from experiments.evaluate_e2 import (
    SYSTEMS,
    SCENARIOS,
    GROUND_TRUTH,
    ACTIONABLE_IMPACT_SCENARIOS,
    UNCERTAINTY_SCENARIOS,
    run_e2_system,
)


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

N_REPETITIONS = 10

RESULTS_DIR = PROJECT_ROOT / "results" / "e2"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

RAW_OUTPUT = RESULTS_DIR / "e2_repetitions.csv"
SUMMARY_OUTPUT = RESULTS_DIR / "e2_repetition_summary.csv"
CHECK_OUTPUT = RESULTS_DIR / "e2_repeatability_check.csv"


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def normalize_impact_set(value):
    """
    Convert an impact-set representation into a deterministic tuple.

    This prevents ordering differences from being interpreted as
    different outcomes.
    """

    if value is None:
        return tuple()

    if isinstance(value, (list, tuple, set)):
        return tuple(sorted(str(x) for x in value))

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return tuple()

        # Handle simple comma-separated representation.
        if "," in value:
            return tuple(
                sorted(
                    x.strip()
                    for x in value.split(",")
                    if x.strip()
                )
            )

        return (value,)

    return (str(value),)


def safe_float(value):
    """
    Convert a value to float when possible.
    """
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_impact_metrics(
    scenario,
    predicted_impact,
):
    """
    Calculate impact precision/recall/F1 for the actionable E2 scenarios.

    Uncertainty-only scenarios are excluded from the primary impact
    evaluation, matching the methodology used in evaluate_e2.py.
    """

    if scenario not in ACTIONABLE_IMPACT_SCENARIOS:
        return None, None, None

    truth = set(
        GROUND_TRUTH[scenario]["impact_set"]
    )

    predicted = set(
        normalize_impact_set(predicted_impact)
    )

    if not truth and not predicted:
        return 1.0, 1.0, 1.0

    if not truth:
        precision = 0.0 if predicted else 1.0
        recall = 1.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0.0
        )
        return precision, recall, f1

    if not predicted:
        return 0.0, 0.0, 0.0

    true_positive = len(truth & predicted)

    precision = true_positive / len(predicted)
    recall = true_positive / len(truth)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = (
            2 * precision * recall
            / (precision + recall)
        )

    return precision, recall, f1


def result_to_record(
    system_name,
    scenario,
    repetition,
    result,
):
    """
    Convert one evaluator result into a flat CSV record.
    """

    expected = GROUND_TRUTH[scenario]

    predicted_decision = result.get("decision")

    actual_impact = normalize_impact_set(
        result.get("impact_set")
    )

    expected_impact = normalize_impact_set(
        expected.get("impact_set")
    )

    precision, recall, f1 = calculate_impact_metrics(
        scenario,
        actual_impact,
    )

    expected_decision = expected["decision"]

    decision_correct = int(
        predicted_decision == expected_decision
    )

    impact_correct = int(
        actual_impact == expected_impact
    )

    uncertainty_case = int(
        scenario in UNCERTAINTY_SCENARIOS
    )

    actionable_case = int(
        scenario in ACTIONABLE_IMPACT_SCENARIOS
    )

    expected_uncertain = int(
        expected_decision == "DEFER_UNCERTAIN"
    )

    correct_deferral = int(
        expected_uncertain
        and predicted_decision == "DEFER_UNCERTAIN"
    )

    unsafe_commit = int(
        expected_uncertain
        and predicted_decision == "COMMIT"
    )

    return {
        "repetition": repetition,
        "system": system_name,
        "scenario": scenario,

        # Expected / predicted outcomes
        "expected_decision": expected_decision,
        "decision": predicted_decision,
        "decision_correct": decision_correct,

        "expected_impact_set": "|".join(expected_impact),
        "impact_set": "|".join(actual_impact),
        "impact_correct": impact_correct,

        # Experiment classification
        "actionable_case": actionable_case,
        "uncertainty_case": uncertainty_case,

        # Impact metrics
        "impact_precision": precision,
        "impact_recall": recall,
        "impact_f1": f1,

        # Adaptation outcome
        "execution_success": result.get(
            "execution_success"
        ),

        "verification_success": result.get(
            "verification_success"
        ),

        "reconfiguration_count": result.get(
            "reconfiguration_count"
        ),

        "rollback": result.get(
            "rollback"
        ),

        "adaptation_attempted": result.get(
            "adaptation_attempted"
        ),

        "verification_attempted": result.get(
            "verification_attempted"
        ),

        "premature_adaptation": result.get(
            "premature_adaptation"
        ),

        # Evidence / assurance
        "assurance": safe_float(
            result.get("assurance")
        ),

        "evidence_status": result.get(
            "evidence_status"
        ),

        "replacement_assurance": safe_float(
            result.get("replacement_assurance")
        ),

        "replacement_status": result.get(
            "replacement_status"
        ),

        # Uncertainty handling
        "correct_deferral": correct_deferral,
        "unsafe_commit": unsafe_commit,

        # Architecture
        "final_architecture": result.get(
            "final_architecture"
        ),
    }


# ---------------------------------------------------------------------
# Main repeatability experiment
# ---------------------------------------------------------------------

def run_repetitions():
    """
    Execute all E2 system/scenario combinations N_REPETITIONS times.
    """

    records = []

    total_cases = (
        len(SYSTEMS)
        * len(SCENARIOS)
        * N_REPETITIONS
    )

    completed = 0

    print("=" * 72)
    print("E2 REPEATABILITY EXPERIMENT")
    print("=" * 72)

    print(
        f"Systems      : {len(SYSTEMS)}"
    )
    print(
        f"Scenarios    : {len(SCENARIOS)}"
    )
    print(
        f"Repetitions  : {N_REPETITIONS}"
    )
    print(
        f"Total runs   : {total_cases}"
    )

    print("=" * 72)

    for repetition in range(1, N_REPETITIONS + 1):

        print(
            f"\nRepetition {repetition}/{N_REPETITIONS}"
        )

        for system_name in SYSTEMS:

            for scenario in SCENARIOS:

                result = run_e2_system(
                    system_name,
                    scenario,
                )

                record = result_to_record(
                    system_name=system_name,
                    scenario=scenario,
                    repetition=repetition,
                    result=result,
                )

                records.append(record)

                completed += 1

                if completed % 50 == 0:
                    print(
                        f"  Progress: "
                        f"{completed}/{total_cases}"
                    )

    df = pd.DataFrame(records)

    df.to_csv(
        RAW_OUTPUT,
        index=False,
    )

    print("\n" + "=" * 72)
    print("RAW REPEATABILITY RESULTS SAVED")
    print("=" * 72)

    print(RAW_OUTPUT)

    return df


# ---------------------------------------------------------------------
# Repetition summary
# ---------------------------------------------------------------------

def build_repetition_summary(df):
    """
    Calculate mean/std/min/max over repetitions.

    Because the experiment is deterministic, the expected standard
    deviation for decision/outcome metrics should be zero.
    """

    numeric_metrics = [
        "decision_correct",
        "impact_correct",
        "impact_precision",
        "impact_recall",
        "impact_f1",
        "execution_success",
        "verification_success",
        "reconfiguration_count",
        "rollback",
        "adaptation_attempted",
        "verification_attempted",
        "premature_adaptation",
        "assurance",
        "replacement_assurance",
        "correct_deferral",
        "unsafe_commit",
    ]

    existing_metrics = [
        m for m in numeric_metrics
        if m in df.columns
    ]

    summary_rows = []

    for system in SYSTEMS:

        subset = df[
            df["system"] == system
        ]

        row = {
            "system": system,
            "total_runs": len(subset),
        }

        for metric in existing_metrics:

            values = pd.to_numeric(
                subset[metric],
                errors="coerce",
            )

            row[f"{metric}_mean"] = values.mean()
            row[f"{metric}_std"] = values.std(
                ddof=0
            )
            row[f"{metric}_min"] = values.min()
            row[f"{metric}_max"] = values.max()

        summary_rows.append(row)

    summary = pd.DataFrame(
        summary_rows
    )

    summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
    )

    print("\n" + "=" * 72)
    print("REPETITION SUMMARY")
    print("=" * 72)

    display_columns = [
        "system",
        "total_runs",
        "decision_correct_mean",
        "decision_correct_std",
        "impact_f1_mean",
        "impact_f1_std",
        "correct_deferral_mean",
        "correct_deferral_std",
        "unsafe_commit_mean",
        "unsafe_commit_std",
        "reconfiguration_count_mean",
        "reconfiguration_count_std",
    ]

    display_columns = [
        c for c in display_columns
        if c in summary.columns
    ]

    print(
        summary[
            display_columns
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print(
        f"\nSaved: {SUMMARY_OUTPUT}"
    )

    return summary


# ---------------------------------------------------------------------
# Repeatability check
# ---------------------------------------------------------------------

def build_repeatability_check(df):
    """
    Check whether each system/scenario produces the same outcome
    across all repetitions.

    We intentionally do NOT require exact equality of floating-point
    assurance values because some scenarios use timestamps generated
    at runtime. The repeatability check therefore focuses on
    decision-level and behavioral outcomes.
    """

    invariant_columns = [
        "decision",
        "impact_set",
        "execution_success",
        "verification_success",
        "reconfiguration_count",
        "rollback",
        "adaptation_attempted",
        "verification_attempted",
        "premature_adaptation",
        "evidence_status",
        "replacement_status",
    ]

    invariant_columns = [
        c for c in invariant_columns
        if c in df.columns
    ]

    rows = []

    for system in SYSTEMS:

        for scenario in SCENARIOS:

            subset = df[
                (df["system"] == system)
                &
                (df["scenario"] == scenario)
            ].copy()

            invariant_results = []

            for column in invariant_columns:

                values = subset[column].astype(
                    str
                ).fillna("<NA>")

                unique_values = (
                    values
                    .drop_duplicates()
                    .tolist()
                )

                invariant_results.append(
                    len(unique_values) == 1
                )

            all_invariants_identical = all(
                invariant_results
            )

            # Decision-level repeatability
            decision_values = (
                subset["decision"]
                .astype(str)
                .unique()
            )

            decision_repeatable = (
                len(decision_values) == 1
            )

            # Impact repeatability
            impact_values = (
                subset["impact_set"]
                .astype(str)
                .unique()
            )

            impact_repeatable = (
                len(impact_values) == 1
            )

            # Reconfiguration repeatability
            recon_values = (
                subset[
                    "reconfiguration_count"
                ]
                .astype(str)
                .unique()
            )

            reconfiguration_repeatable = (
                len(recon_values) == 1
            )

            # Behavioral repeatability
            behavior_repeatable = all(
                [
                    decision_repeatable,
                    impact_repeatable,
                    reconfiguration_repeatable,
                ]
            )

            rows.append(
                {
                    "system": system,
                    "scenario": scenario,
                    "repetitions": len(subset),

                    "decision_repeatable":
                        int(decision_repeatable),

                    "impact_repeatable":
                        int(impact_repeatable),

                    "reconfiguration_repeatable":
                        int(
                            reconfiguration_repeatable
                        ),

                    "behavior_repeatable":
                        int(behavior_repeatable),

                    "all_invariants_identical":
                        int(
                            all_invariants_identical
                        ),
                }
            )

    check = pd.DataFrame(rows)

    check.to_csv(
        CHECK_OUTPUT,
        index=False,
    )

    print("\n" + "=" * 72)
    print("REPEATABILITY CHECK")
    print("=" * 72)

    print(
        check.to_string(
            index=False
        )
    )

    total_groups = len(check)

    behavior_repeatability_rate = (
        check["behavior_repeatable"].mean()
    )

    full_invariant_rate = (
        check["all_invariants_identical"].mean()
    )

    print("\n" + "-" * 72)

    print(
        f"System/scenario groups : {total_groups}"
    )

    print(
        "Behavior repeatability : "
        f"{behavior_repeatability_rate:.1%}"
    )

    print(
        "Full invariant equality : "
        f"{full_invariant_rate:.1%}"
    )

    print("-" * 72)

    if behavior_repeatability_rate == 1.0:
        print(
            "PASS: All system/scenario outcomes "
            "are behaviorally repeatable."
        )
    else:
        print(
            "WARNING: Some system/scenario outcomes "
            "are not behaviorally repeatable."
        )

    print(
        f"\nSaved: {CHECK_OUTPUT}"
    )

    return check


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    df = run_repetitions()

    build_repetition_summary(df)

    check = build_repeatability_check(df)

    print("\n" + "=" * 72)
    print("E2 REPEATABILITY EXPERIMENT COMPLETE")
    print("=" * 72)

    print(
        f"Total executions: {len(df)}"
    )

    print(
        f"Expected executions: "
        f"{len(SYSTEMS) * len(SCENARIOS) * N_REPETITIONS}"
    )

    print(
        "\nGenerated files:"
    )

    print(
        f"  {RAW_OUTPUT}"
    )

    print(
        f"  {SUMMARY_OUTPUT}"
    )

    print(
        f"  {CHECK_OUTPUT}"
    )

    behavior_rate = (
        check["behavior_repeatable"].mean()
    )

    print(
        "\nFinal behavioral repeatability: "
        f"{behavior_rate:.1%}"
    )

    print("=" * 72)


if __name__ == "__main__":
    main()