# experiments/evaluate_e2.py

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from experiments.e2_baseline_systems import run_e2_system


# =====================================================================
# SYSTEMS
# =====================================================================

SYSTEMS = [
    "B1_STATIC",
    "B2_DYNAMIC",
    "B3_UNTYPED",
    "B4_RASE_NO_EAS",
    "B5_RASE",
    "B6_MAPEK",
]


# =====================================================================
# SCENARIOS
# =====================================================================

SCENARIOS = [
    "S0_NORMAL",
    "S1_REPLACEMENT_PASS",
    "S2_REPLACEMENT_FAIL",
    "S3_NO_REPLACEMENT",
    "S4_IRRELEVANT_BRANCH",
    "S5_UNCERTAIN_REPLACEMENT_EVIDENCE",
    "S6_STALE_EVIDENCE",
    "S7_CONTRADICTORY_EVIDENCE",
    "S8_DELAYED_OBSERVATION",
    "S9_DEGRADED_AGENT",
    "S10_WEAK_REPLACEMENT",
]


# =====================================================================
# GROUND TRUTH
# =====================================================================

GROUND_TRUTH = {

    "S0_NORMAL": {
        "decision": "NO_ADAPTATION",
        "impact_set": [],
    },

    "S1_REPLACEMENT_PASS": {
        "decision": "COMMIT",
        "impact_set": ["A2", "A3"],
    },

    "S2_REPLACEMENT_FAIL": {
        "decision": "ROLLBACK",
        "impact_set": ["A2", "A3"],
    },

    "S3_NO_REPLACEMENT": {
        "decision": "NO_REPLACEMENT",
        "impact_set": ["A2", "A3"],
    },

    "S4_IRRELEVANT_BRANCH": {
        "decision": "NO_REPLACEMENT",
        "impact_set": ["A2", "A3"],
    },

    "S5_UNCERTAIN_REPLACEMENT_EVIDENCE": {
        "decision": "DEFER_UNCERTAIN",
        "impact_set": ["A2", "A3"],
    },

    "S6_STALE_EVIDENCE": {
        "decision": "DEFER_UNCERTAIN",
        "impact_set": ["A2", "A3"],
    },

    "S7_CONTRADICTORY_EVIDENCE": {
        "decision": "DEFER_UNCERTAIN",
        "impact_set": ["A2", "A3"],
    },

    "S8_DELAYED_OBSERVATION": {
        "decision": "COMMIT",
        "impact_set": ["A2", "A3"],
    },

    "S9_DEGRADED_AGENT": {
        "decision": "DEFER_UNCERTAIN",
        "impact_set": ["A2", "A3"],
    },

    "S10_WEAK_REPLACEMENT": {
        "decision": "DEFER_UNCERTAIN",
        "impact_set": ["A2", "A3"],
    },
}


# =====================================================================
# SCENARIO GROUPS
# =====================================================================

ACTIONABLE_IMPACT_SCENARIOS = {
    "S1_REPLACEMENT_PASS",
    "S2_REPLACEMENT_FAIL",
    "S3_NO_REPLACEMENT",
    "S4_IRRELEVANT_BRANCH",
    "S8_DELAYED_OBSERVATION",
}


UNCERTAINTY_SCENARIOS = {
    "S5_UNCERTAIN_REPLACEMENT_EVIDENCE",
    "S6_STALE_EVIDENCE",
    "S7_CONTRADICTORY_EVIDENCE",
    "S9_DEGRADED_AGENT",
    "S10_WEAK_REPLACEMENT",
}


# =====================================================================
# METRIC HELPERS
# =====================================================================

def set_metrics(predicted, expected):
    """
    Compute set-based precision, recall, and F1.
    """

    predicted = set(predicted or [])
    expected = set(expected or [])

    if not predicted and not expected:
        return 1.0, 1.0, 1.0

    true_positive = len(
        predicted & expected
    )

    false_positive = len(
        predicted - expected
    )

    false_negative = len(
        expected - predicted
    )

    precision_denominator = (
        true_positive + false_positive
    )

    recall_denominator = (
        true_positive + false_negative
    )

    precision = (
        true_positive / precision_denominator
        if precision_denominator > 0
        else 0.0
    )

    recall = (
        true_positive / recall_denominator
        if recall_denominator > 0
        else 0.0
    )

    if precision + recall > 0:
        f1 = (
            2.0
            * precision
            * recall
            / (precision + recall)
        )
    else:
        f1 = 0.0

    return precision, recall, f1


def safe_mean(series):
    """
    Return a mean while safely handling an empty series.
    """

    if len(series) == 0:
        return float("nan")

    return series.mean()


def rate(df, column):
    """
    Mean of a Boolean/integer indicator.
    """

    if len(df) == 0:
        return float("nan")

    return df[column].mean()


# =====================================================================
# MAIN EVALUATION
# =====================================================================

def main():

    print()
    print("=" * 72)
    print("RASE E2 RUNTIME UNCERTAINTY VALIDATION")
    print("=" * 72)
    print()

    print(
        "Validation mode: 1 run per system/scenario"
    )

    print(
        f"Systems: {len(SYSTEMS)}"
    )

    print(
        f"Scenarios: {len(SCENARIOS)}"
    )

    print(
        f"Total cases: "
        f"{len(SYSTEMS) * len(SCENARIOS)}"
    )

    print()

    records = []

    total = (
        len(SYSTEMS)
        * len(SCENARIOS)
    )

    completed = 0

    # =================================================================
    # RUN ALL CASES
    # =================================================================

    for scenario in SCENARIOS:

        print(
            f"Running scenario: {scenario}"
        )

        expected = GROUND_TRUTH[
            scenario
        ]

        for system in SYSTEMS:

            result = run_e2_system(
                system,
                scenario,
            )

            predicted_decision = result.get(
                "decision",
                "",
            )

            expected_decision = expected[
                "decision"
            ]

            decision_correct = int(
                predicted_decision
                == expected_decision
            )

            # ---------------------------------------------------------
            # Raw architectural impact
            # ---------------------------------------------------------

            predicted_impact = result.get(
                "impact_set",
                [],
            )

            expected_impact = expected[
                "impact_set"
            ]

            raw_precision, raw_recall, raw_f1 = (
                set_metrics(
                    predicted_impact,
                    expected_impact,
                )
            )

            # ---------------------------------------------------------
            # Impact evaluation policy
            # ---------------------------------------------------------

            impact_evaluable = int(
                scenario in ACTIONABLE_IMPACT_SCENARIOS
            )

            if impact_evaluable:
                impact_precision = raw_precision
                impact_recall = raw_recall
                impact_f1 = raw_f1
            else:
                impact_precision = float("nan")
                impact_recall = float("nan")
                impact_f1 = float("nan")

            # ---------------------------------------------------------
            # Uncertainty
            # ---------------------------------------------------------

            uncertainty_case = int(
                scenario in UNCERTAINTY_SCENARIOS
            )

            expected_uncertain = int(
                expected_decision
                == "DEFER_UNCERTAIN"
            )

            predicted_uncertain = int(
                predicted_decision
                == "DEFER_UNCERTAIN"
            )

            correct_deferral = int(
                expected_uncertain
                and predicted_uncertain
            )

            # ---------------------------------------------------------
            # Unsafe commit
            # ---------------------------------------------------------

            unsafe_commit = int(
                expected_uncertain
                and predicted_decision == "COMMIT"
            )

            # ---------------------------------------------------------
            # Decision-specific correctness
            # ---------------------------------------------------------

            correct_commit = int(
                expected_decision == "COMMIT"
                and predicted_decision == "COMMIT"
            )

            correct_rollback = int(
                expected_decision == "ROLLBACK"
                and predicted_decision == "ROLLBACK"
            )

            correct_no_replacement = int(
                expected_decision == "NO_REPLACEMENT"
                and predicted_decision == "NO_REPLACEMENT"
            )

            correct_no_adaptation = int(
                expected_decision == "NO_ADAPTATION"
                and predicted_decision == "NO_ADAPTATION"
            )

            # ---------------------------------------------------------
            # Premature adaptation
            # ---------------------------------------------------------

            premature_adaptation = bool(
                result.get(
                    "premature_adaptation",
                    False,
                )
            )

            # ---------------------------------------------------------
            # Evidence-specific indicators
            # ---------------------------------------------------------

            evidence_status = result.get(
                "evidence_status",
                "",
            )

            replacement_status = result.get(
                "replacement_status",
                "",
            )

            stale_detection = int(
                scenario == "S6_STALE_EVIDENCE"
                and evidence_status
                in {
                    "UNCERTAIN",
                    "UNCERTAIN_CONFLICT",
                }
            )

            contradiction_detection = int(
                scenario == "S7_CONTRADICTORY_EVIDENCE"
                and evidence_status
                == "UNCERTAIN_CONFLICT"
            )

            weak_replacement_detection = int(
                scenario == "S10_WEAK_REPLACEMENT"
                and replacement_status
                == "UNCERTAIN"
            )

            degraded_detection = int(
                scenario == "S9_DEGRADED_AGENT"
                and evidence_status
                in {
                    "UNCERTAIN",
                    "UNCERTAIN_CONFLICT",
                }
            )

            # ---------------------------------------------------------
            # Correct uncertainty handling
            # ---------------------------------------------------------

            uncertainty_handling_correct = int(
                not uncertainty_case
                or (
                    expected_uncertain
                    and predicted_uncertain
                )
            )

            # ---------------------------------------------------------
            # Adaptation / verification
            # ---------------------------------------------------------

            reconfiguration_count = result.get(
                "reconfiguration_count",
                0,
            )

            execution_success = bool(
                result.get(
                    "execution_success",
                    False,
                )
            )

            verification_success = bool(
                result.get(
                    "verification_success",
                    False,
                )
            )

            rollback = bool(
                result.get(
                    "rollback",
                    False,
                )
            )

            # A reconfiguration attempt is represented by a
            # non-zero reconfiguration count.
            adaptation_attempted = int(
                reconfiguration_count > 0
            )

            # Verification is considered attempted whenever the
            # system has performed a reconfiguration attempt.
            verification_attempted = int(
                adaptation_attempted
            )

            # ---------------------------------------------------------
            # Unnecessary reconfiguration
            # ---------------------------------------------------------

            no_adaptation_expected = (
                expected_decision
                in {
                    "NO_ADAPTATION",
                    "NO_REPLACEMENT",
                    "DEFER_UNCERTAIN",
                }
            )

            unnecessary_reconfiguration = int(
                no_adaptation_expected
                and reconfiguration_count > 0
            )

            # ---------------------------------------------------------
            # Record
            # ---------------------------------------------------------

            record = {

                # Identity
                "system": system,
                "scenario": scenario,

                # Decision
                "decision": predicted_decision,
                "expected_decision": expected_decision,
                "decision_correct": decision_correct,

                "correct_commit": correct_commit,
                "correct_rollback": correct_rollback,
                "correct_no_replacement": (
                    correct_no_replacement
                ),
                "correct_no_adaptation": (
                    correct_no_adaptation
                ),

                # Uncertainty
                "uncertainty_case": uncertainty_case,
                "expected_uncertain": expected_uncertain,
                "predicted_uncertain": predicted_uncertain,
                "correct_deferral": correct_deferral,
                "unsafe_commit": unsafe_commit,

                "uncertainty_handling_correct": (
                    uncertainty_handling_correct
                ),

                # Architectural impact
                "impact_evaluable": impact_evaluable,

                "raw_impact_precision": raw_precision,
                "raw_impact_recall": raw_recall,
                "raw_impact_f1": raw_f1,

                "impact_precision": impact_precision,
                "impact_recall": impact_recall,
                "impact_f1": impact_f1,

                "impact_set": "|".join(
                    predicted_impact
                ),

                "expected_impact_set": "|".join(
                    expected_impact
                ),

                # Evidence
                "assurance": result.get(
                    "assurance",
                    None,
                ),

                "evidence_status": evidence_status,

                "replacement_assurance": result.get(
                    "replacement_assurance",
                    None,
                ),

                "replacement_status": replacement_status,

                "stale_detection": stale_detection,

                "contradiction_detection": (
                    contradiction_detection
                ),

                "weak_replacement_detection": (
                    weak_replacement_detection
                ),

                "degraded_detection": (
                    degraded_detection
                ),

                # Execution / verification
                "execution_success": (
                    execution_success
                ),

                "verification_success": (
                    verification_success
                ),

                "adaptation_attempted": (
                    adaptation_attempted
                ),

                "verification_attempted": (
                    verification_attempted
                ),

                # Adaptation
                "reconfiguration_count": (
                    reconfiguration_count
                ),

                "unnecessary_reconfiguration": (
                    unnecessary_reconfiguration
                ),

                "rollback": rollback,

                "premature_adaptation": (
                    premature_adaptation
                ),

                # Final state
                "final_architecture": result.get(
                    "final_architecture",
                    "",
                ),
            }

            records.append(record)

            completed += 1

            print(
                f"  {system}: "
                f"{predicted_decision}"
            )

        print(
            f"  completed: "
            f"{completed}/{total}"
        )

        print()

    # =================================================================
    # DATAFRAME
    # =================================================================

    df = pd.DataFrame(
        records
    )

    boolean_columns = [
        "execution_success",
        "verification_success",
        "rollback",
    ]

    for column in boolean_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .astype(bool)
                .astype(int)
            )

    # =================================================================
    # OUTPUT DIRECTORY
    # =================================================================

    output_dir = (
        PROJECT_ROOT
        / "results"
        / "e2"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =================================================================
    # RAW RESULTS
    # =================================================================

    runs_file = (
        output_dir
        / "e2_runs.csv"
    )

    df.to_csv(
        runs_file,
        index=False,
    )

    # =================================================================
    # PRIMARY SYSTEM SUMMARY
    # =================================================================

    summary_records = []

    for system in SYSTEMS:

        system_df = df[
            df["system"] == system
        ]

        actionable_df = system_df[
            system_df["impact_evaluable"] == 1
        ]

        uncertainty_df = system_df[
            system_df["uncertainty_case"] == 1
        ]

        # -------------------------------------------------------------
        # Decision-specific subsets
        # -------------------------------------------------------------

        commit_required_df = system_df[
            system_df["expected_decision"] == "COMMIT"
        ]

        rollback_required_df = system_df[
            system_df["expected_decision"] == "ROLLBACK"
        ]

        no_replacement_required_df = system_df[
            system_df["expected_decision"]
            == "NO_REPLACEMENT"
        ]

        no_adaptation_required_df = system_df[
            system_df["expected_decision"]
            == "NO_ADAPTATION"
        ]

        # -------------------------------------------------------------
        # Adaptation attempts
        # -------------------------------------------------------------

        verification_attempt_df = system_df[
            system_df["verification_attempted"] == 1
        ]

        summary_records.append({

            "system": system,

            # =========================================================
            # PRIMARY DECISION QUALITY
            # =========================================================

            "decision_accuracy": rate(
                system_df,
                "decision_correct",
            ),

            "correct_commit_rate": rate(
                system_df,
                "correct_commit",
            ),

            "correct_rollback_rate": rate(
                system_df,
                "correct_rollback",
            ),

            "correct_no_replacement_rate": rate(
                system_df,
                "correct_no_replacement",
            ),

            "correct_no_adaptation_rate": rate(
                system_df,
                "correct_no_adaptation",
            ),

            # =========================================================
            # CONDITION-SPECIFIC DECISION ACCURACY
            # =========================================================

            "commit_accuracy_when_required": rate(
                commit_required_df,
                "correct_commit",
            ),

            "rollback_accuracy_when_required": rate(
                rollback_required_df,
                "correct_rollback",
            ),

            "no_replacement_accuracy_when_required": rate(
                no_replacement_required_df,
                "correct_no_replacement",
            ),

            "no_adaptation_accuracy_when_required": rate(
                no_adaptation_required_df,
                "correct_no_adaptation",
            ),

            # =========================================================
            # ARCHITECTURAL IMPACT
            # =========================================================

            "impact_precision": safe_mean(
                actionable_df[
                    "impact_precision"
                ]
            ),

            "impact_recall": safe_mean(
                actionable_df[
                    "impact_recall"
                ]
            ),

            "impact_f1": safe_mean(
                actionable_df[
                    "impact_f1"
                ]
            ),

            # =========================================================
            # UNCERTAINTY SAFETY
            # =========================================================

            "correct_deferral_rate": (
                rate(
                    uncertainty_df,
                    "correct_deferral",
                )
            ),

            "unsafe_commit_rate": (
                rate(
                    uncertainty_df,
                    "unsafe_commit",
                )
            ),

            "uncertainty_handling_accuracy": (
                rate(
                    uncertainty_df,
                    "uncertainty_handling_correct",
                )
            ),

            # =========================================================
            # EVIDENCE REASONING
            # =========================================================

            "stale_detection_rate": (
                rate(
                    uncertainty_df[
                        uncertainty_df["scenario"]
                        == "S6_STALE_EVIDENCE"
                    ],
                    "stale_detection",
                )
            ),

            "contradiction_detection_rate": (
                rate(
                    uncertainty_df[
                        uncertainty_df["scenario"]
                        == "S7_CONTRADICTORY_EVIDENCE"
                    ],
                    "contradiction_detection",
                )
            ),

            "degraded_detection_rate": (
                rate(
                    uncertainty_df[
                        uncertainty_df["scenario"]
                        == "S9_DEGRADED_AGENT"
                    ],
                    "degraded_detection",
                )
            ),

            "weak_replacement_detection_rate": (
                rate(
                    uncertainty_df[
                        uncertainty_df["scenario"]
                        == "S10_WEAK_REPLACEMENT"
                    ],
                    "weak_replacement_detection",
                )
            ),

            # =========================================================
            # ADAPTATION EFFICIENCY
            # =========================================================

            "avg_reconfiguration": safe_mean(
                system_df[
                    "reconfiguration_count"
                ]
            ),

            "unnecessary_reconfiguration_rate": (
                rate(
                    system_df,
                    "unnecessary_reconfiguration",
                )
            ),

            "rollback_rate": rate(
                system_df,
                "rollback",
            ),

            # =========================================================
            # VERIFICATION
            # =========================================================
            #
            # Keep the original all-case metric for traceability.
            #

            "verification_success_rate_all_cases": rate(
                system_df,
                "verification_success",
            ),

            # New scientifically meaningful metric:
            # verification success among attempted adaptations.
            "verification_success_rate_attempted": rate(
                verification_attempt_df,
                "verification_success",
            ),

            "verification_attempt_rate": rate(
                system_df,
                "verification_attempted",
            ),

            "adaptation_attempt_rate": rate(
                system_df,
                "adaptation_attempted",
            ),

            # =========================================================
            # TEMPORAL SAFETY
            # =========================================================

            "premature_adaptation_rate": rate(
                system_df,
                "premature_adaptation",
            ),
        })

    summary = pd.DataFrame(
        summary_records
    )

    summary_file = (
        output_dir
        / "e2_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False,
    )

    # =================================================================
    # SCENARIO-LEVEL SUMMARY
    # =================================================================

    scenario_summary = (
        df.groupby(
            [
                "system",
                "scenario",
            ],
            dropna=False,
        )
        .agg(
            decision_accuracy=(
                "decision_correct",
                "mean",
            ),

            expected_decision=(
                "expected_decision",
                "first",
            ),

            predicted_decision=(
                "decision",
                "first",
            ),

            uncertainty_case=(
                "uncertainty_case",
                "first",
            ),

            correct_deferral=(
                "correct_deferral",
                "mean",
            ),

            unsafe_commit=(
                "unsafe_commit",
                "mean",
            ),

            impact_evaluable=(
                "impact_evaluable",
                "first",
            ),

            impact_precision=(
                "impact_precision",
                "mean",
            ),

            impact_recall=(
                "impact_recall",
                "mean",
            ),

            impact_f1=(
                "impact_f1",
                "mean",
            ),

            raw_impact_precision=(
                "raw_impact_precision",
                "mean",
            ),

            raw_impact_recall=(
                "raw_impact_recall",
                "mean",
            ),

            raw_impact_f1=(
                "raw_impact_f1",
                "mean",
            ),

            assurance=(
                "assurance",
                "mean",
            ),

            replacement_assurance=(
                "replacement_assurance",
                "mean",
            ),

            reconfiguration_count=(
                "reconfiguration_count",
                "mean",
            ),

            unnecessary_reconfiguration=(
                "unnecessary_reconfiguration",
                "mean",
            ),

            rollback=(
                "rollback",
                "mean",
            ),

            execution_success=(
                "execution_success",
                "mean",
            ),

            verification_attempted=(
                "verification_attempted",
                "mean",
            ),

            verification_success=(
                "verification_success",
                "mean",
            ),

            premature_adaptation=(
                "premature_adaptation",
                "mean",
            ),
        )
        .reset_index()
    )

    scenario_file = (
        output_dir
        / "e2_scenario_summary.csv"
    )

    scenario_summary.to_csv(
        scenario_file,
        index=False,
    )

    # =================================================================
    # UNCERTAINTY-ONLY SUMMARY
    # =================================================================

    uncertainty_summary = (
        df[
            df["uncertainty_case"] == 1
        ]
        .groupby("system")
        .agg(
            uncertainty_cases=(
                "uncertainty_case",
                "sum",
            ),

            correct_deferral_rate=(
                "correct_deferral",
                "mean",
            ),

            unsafe_commit_rate=(
                "unsafe_commit",
                "mean",
            ),

            uncertainty_handling_accuracy=(
                "uncertainty_handling_correct",
                "mean",
            ),

            avg_assurance=(
                "assurance",
                "mean",
            ),

            avg_replacement_assurance=(
                "replacement_assurance",
                "mean",
            ),

            avg_reconfiguration=(
                "reconfiguration_count",
                "mean",
            ),
        )
        .reset_index()
    )

    uncertainty_file = (
        output_dir
        / "e2_uncertainty_summary.csv"
    )

    uncertainty_summary.to_csv(
        uncertainty_file,
        index=False,
    )

    # =================================================================
    # TERMINAL SUMMARY
    # =================================================================

    print()
    print("=" * 72)
    print("E2 VALIDATION SUMMARY")
    print("=" * 72)
    print()

    print(
        summary.to_string(
            index=False,
            float_format=lambda x:
                f"{x:.3f}",
        )
    )

    print()
    print("=" * 72)
    print("UNCERTAINTY SAFETY SUMMARY")
    print("=" * 72)
    print()

    print(
        uncertainty_summary.to_string(
            index=False,
            float_format=lambda x:
                f"{x:.3f}",
        )
    )

    print()
    print("=" * 72)
    print("SCENARIO DECISIONS")
    print("=" * 72)
    print()

    decision_view = scenario_summary[
        [
            "system",
            "scenario",
            "expected_decision",
            "predicted_decision",
            "decision_accuracy",
            "correct_deferral",
            "unsafe_commit",
            "verification_attempted",
            "verification_success",
        ]
    ]

    print(
        decision_view.to_string(
            index=False,
            float_format=lambda x:
                f"{x:.3f}",
        )
    )

    print()
    print(
        f"Total evaluated cases: "
        f"{len(df)}"
    )

    print()
    print("Output files:")
    print(
        runs_file
    )
    print(
        summary_file
    )
    print(
        scenario_file
    )
    print(
        uncertainty_file
    )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()