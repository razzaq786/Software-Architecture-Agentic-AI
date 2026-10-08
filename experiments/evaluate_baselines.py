from pathlib import Path
import sys
import csv
import statistics

# Allow imports when running:
# python .\experiments\evaluate_baselines.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_common import SCENARIOS
from experiments.baseline_systems import (
    create_agents,
    run_static,
    run_dynamic,
    run_untyped,
    run_rase_no_eas,
    run_rase,
    run_mapek,
)


RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

REPETITIONS = 10


SYSTEMS = {
    "B1_STATIC": run_static,
    "B2_DYNAMIC": run_dynamic,
    "B3_UNTYPED": run_untyped,
    "B4_RASE_NO_EAS": run_rase_no_eas,
    "B5_RASE": run_rase,
    "B6_MAPEK": run_mapek,
}


def scenario_configuration(scenario):
    """
    Explicitly controls every scenario so that state does not leak
    between repetitions or between scenarios.
    """
    configurations = {
        "S0_NORMAL": {
            "include_replacement": True,
            "degraded": False,
        },
        "S1_REPLACEMENT_PASS": {
            "include_replacement": True,
            "degraded": False,
        },
        "S2_REPLACEMENT_FAIL": {
            "include_replacement": True,
            "degraded": True,
        },
        "S3_NO_REPLACEMENT": {
            "include_replacement": False,
            "degraded": False,
        },
        "S4_IRRELEVANT_BRANCH": {
            "include_replacement": False,
            "degraded": False,
        },
        "S5_UNCERTAIN_REPLACEMENT_EVIDENCE": {
            "include_replacement": True,
            "degraded": False,
        },
    }

    if scenario not in configurations:
        raise ValueError(f"Unknown scenario: {scenario}")

    return configurations[scenario]

def normalize_functional_architecture(architecture):
    """
    Convert different architecture notations into the same canonical
    set of directed functional edges.

    Examples:

        A1->A2->A3
        A1->A2|A2->A3

    both become:

        A1->A2|A2->A3

    Observational relationships such as A4->A2 are excluded from
    functional architecture evaluation.
    """

    if not architecture:
        return ""

    parts = architecture.split("|")

    edges = set()

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Observational relationship: retained in RASE's richer
        # architectural state but excluded from functional workflow
        # accuracy.
        if part == "A4->A2":
            continue

        nodes = [
            node.strip()
            for node in part.split("->")
            if node.strip()
        ]

        if len(nodes) < 2:
            continue

        # Convert a chain such as:
        #
        # A1->A2->A3
        #
        # into:
        #
        # A1->A2
        # A2->A3

        for source, target in zip(nodes, nodes[1:]):
            edges.add(f"{source}->{target}")

    return "|".join(sorted(edges))


def normalize_impact(impact_set):
    if impact_set is None:
        return set()

    return set(impact_set)


def impact_metrics(predicted, expected):
    """
    Calculate precision, recall and F1 for affected-agent prediction.
    """
    predicted = normalize_impact(predicted)
    expected = normalize_impact(expected)

    true_positive = len(predicted & expected)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)

    if true_positive + false_positive == 0:
        precision = 1.0 if not expected and not predicted else 0.0
    else:
        precision = true_positive / (true_positive + false_positive)

    if true_positive + false_negative == 0:
        recall = 1.0
    else:
        recall = true_positive / (true_positive + false_negative)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return precision, recall, f1


def expected_functional_architecture(scenario):
    """
    Ground-truth functional architecture.

    S4 and S5 contain an observational A4->A2 relationship in the
    richer architectural state, but it is intentionally ignored for
    functional architecture accuracy.
    """
    architecture = SCENARIOS[scenario].expected_final_architecture
    return normalize_functional_architecture(architecture)


def evaluate_result(scenario, system_name, result, repetition):
    ground_truth = SCENARIOS[scenario]

    predicted_decision = result.get("decision")
    expected_decision = ground_truth.expected_decision

    decision_correct = (
        predicted_decision == expected_decision
    )

    predicted_architecture = normalize_functional_architecture(
        result.get("final_architecture", "")
    )

    expected_architecture = expected_functional_architecture(
        scenario
    )

    architecture_correct = (
        predicted_architecture == expected_architecture
    )

    predicted_impact = result.get("impact_set", [])
    expected_impact = ground_truth.affected_agents

    precision, recall, f1 = impact_metrics(
        predicted_impact,
        expected_impact,
    )

    # Adaptation is considered correct when the system makes the
    # correct high-level architectural decision.
    adaptation_correct = decision_correct

    # A reconfiguration is unnecessary when it occurs despite the
    # ground truth saying that no architectural adaptation should
    # be committed or performed.
    reconfiguration_count = result.get(
        "reconfiguration_count", 0
    )

    unnecessary_reconfiguration = (
        reconfiguration_count > 0
        and expected_decision
        not in {"COMMIT", "ROLLBACK"}
    )

    rollback_correct = (
        bool(result.get("rollback", False))
        == (expected_decision == "ROLLBACK")
    )

    return {
        "repetition": repetition,
        "scenario": scenario,
        "system": system_name,

        "decision": predicted_decision,
        "expected_decision": expected_decision,
        "decision_correct": int(decision_correct),

        "execution_success": int(
            bool(result.get("execution_success", False))
        ),
        "verification_success": int(
            bool(result.get("verification_success", False))
        ),

        "reconfiguration_count": reconfiguration_count,
        "rollback": int(
            bool(result.get("rollback", False))
        ),
        "rollback_correct": int(rollback_correct),
        "unnecessary_reconfiguration": int(
            unnecessary_reconfiguration
        ),

        "predicted_architecture": predicted_architecture,
        "expected_architecture": expected_architecture,
        "architecture_correct": int(architecture_correct),

        "predicted_impact": ",".join(
            sorted(normalize_impact(predicted_impact))
        ),
        "expected_impact": ",".join(
            sorted(normalize_impact(expected_impact))
        ),

        "impact_precision": precision,
        "impact_recall": recall,
        "impact_f1": f1,

        "adaptation_correct": int(adaptation_correct),

        "replacement_assurance": result.get(
            "replacement_assurance", ""
        ),
    }


def run_single(system_name, runner, scenario):
    """
    Create completely fresh agents for every individual run.
    """
    config = scenario_configuration(scenario)

    a1, a2, a2_prime, a3, a4 = create_agents(
        include_replacement=config["include_replacement"],
        degraded_replacement=config["degraded"],
    )

    result = runner(
        scenario,
        a1,
        a2,
        a2_prime,
        a3,
        a4,
    )

    return result


def write_csv(path, rows):
    if not rows:
        return

    fieldnames = list(rows[0].keys())

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def mean(rows, field):
    values = []

    for row in rows:
        value = row.get(field)

        if value is None or value == "":
            continue

        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    if not values:
        return 0.0

    return statistics.mean(values)


def summarize(all_rows):
    summary_rows = []

    for system_name in SYSTEMS:
        system_rows = [
            row
            for row in all_rows
            if row["system"] == system_name
        ]

        summary_rows.append(
            {
                "system": system_name,
                "runs": len(system_rows),

                "decision_accuracy": mean(
                    system_rows,
                    "decision_correct",
                ),

                "functional_architecture_accuracy": mean(
                    system_rows,
                    "architecture_correct",
                ),

                "impact_precision": mean(
                    system_rows,
                    "impact_precision",
                ),

                "impact_recall": mean(
                    system_rows,
                    "impact_recall",
                ),

                "impact_f1": mean(
                    system_rows,
                    "impact_f1",
                ),

                "adaptation_correct": mean(
                    system_rows,
                    "adaptation_correct",
                ),

                "execution_success_rate": mean(
                    system_rows,
                    "execution_success",
                ),

                "verification_success_rate": mean(
                    system_rows,
                    "verification_success",
                ),

                "rollback_correctness": mean(
                    system_rows,
                    "rollback_correct",
                ),

                "unnecessary_reconfiguration_rate": mean(
                    system_rows,
                    "unnecessary_reconfiguration",
                ),

                "mean_reconfiguration_count": mean(
                    system_rows,
                    "reconfiguration_count",
                ),
            }
        )

    return summary_rows


def summarize_impact_by_scenario(all_rows):
    rows = []

    for system_name in SYSTEMS:
        for scenario in SCENARIOS:
            selected = [
                row
                for row in all_rows
                if row["system"] == system_name
                and row["scenario"] == scenario
            ]

            if not selected:
                continue

            rows.append(
                {
                    "system": system_name,
                    "scenario": scenario,
                    "runs": len(selected),

                    "impact_precision": mean(
                        selected,
                        "impact_precision",
                    ),

                    "impact_recall": mean(
                        selected,
                        "impact_recall",
                    ),

                    "impact_f1": mean(
                        selected,
                        "impact_f1",
                    ),

                    "decision_accuracy": mean(
                        selected,
                        "decision_correct",
                    ),

                    "architecture_accuracy": mean(
                        selected,
                        "architecture_correct",
                    ),
                }
            )

    return rows


def print_summary(summary_rows):
    print()
    print("=" * 100)
    print("BASELINE EVALUATION SUMMARY")
    print("=" * 100)

    header = (
        f"{'System':<20}"
        f"{'Decision':>12}"
        f"{'Arch.':>12}"
        f"{'Impact P':>12}"
        f"{'Impact R':>12}"
        f"{'Impact F1':>12}"
        f"{'Adapt.':>12}"
    )

    print(header)
    print("-" * len(header))

    for row in summary_rows:
        print(
            f"{row['system']:<20}"
            f"{row['decision_accuracy']:>11.3f}"
            f"{row['functional_architecture_accuracy']:>11.3f}"
            f"{row['impact_precision']:>11.3f}"
            f"{row['impact_recall']:>11.3f}"
            f"{row['impact_f1']:>11.3f}"
            f"{row['adaptation_correct']:>11.3f}"
        )

    print("=" * 100)


def main():
    print()
    print("RASE Baseline Evaluation")
    print(f"Repetitions per scenario/system: {REPETITIONS}")
    print()

    all_rows = []

    total_runs = (
        len(SCENARIOS)
        * len(SYSTEMS)
        * REPETITIONS
    )

    completed = 0

    for scenario in SCENARIOS:

        print(f"Running scenario: {scenario}")

        for system_name, runner in SYSTEMS.items():

            for repetition in range(1, REPETITIONS + 1):

                result = run_single(
                    system_name,
                    runner,
                    scenario,
                )

                row = evaluate_result(
                    scenario,
                    system_name,
                    result,
                    repetition,
                )

                all_rows.append(row)

                completed += 1

        print(
            f"  completed: "
            f"{completed}/{total_runs}"
        )

    summary_rows = summarize(all_rows)

    impact_rows = summarize_impact_by_scenario(
        all_rows
    )

    raw_path = RESULTS_DIR / "baseline_runs.csv"
    summary_path = RESULTS_DIR / "baseline_summary.csv"
    impact_path = RESULTS_DIR / "impact_metrics.csv"

    write_csv(
        raw_path,
        all_rows,
    )

    write_csv(
        summary_path,
        summary_rows,
    )

    write_csv(
        impact_path,
        impact_rows,
    )

    print_summary(summary_rows)

    print()
    print("Files written:")
    print(f"  {raw_path}")
    print(f"  {summary_path}")
    print(f"  {impact_path}")
    print()

    print(
        f"Total evaluated runs: {len(all_rows)}"
    )


if __name__ == "__main__":
    main()