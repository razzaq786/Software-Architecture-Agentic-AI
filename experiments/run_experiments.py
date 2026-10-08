import sys
import os
import csv
import time
import random
from pathlib import Path


# =========================================================
# Project path
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# Imports
# =========================================================

from agents.agents import (
    VisitAnalysisAgent,
    VetAssignmentAgent,
    VerificationAgent
)

from rase.rase_runtime import RASERuntime


# =========================================================
# Experiment configuration
# =========================================================

REPETITIONS = 10

SCENARIOS = [
    "S0_NORMAL",
    "S1_UNAVAILABLE",
    "S2_DEGRADED",
    "S3_PASS",
    "S4_FAIL"
]

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"

RESULTS_FILE = RESULTS_DIR / "rase_pilot_results.csv"


# =========================================================
# Utility
# =========================================================

def now_ms():
    return time.perf_counter() * 1000.0


# =========================================================
# Create RASE runtime
# =========================================================

def create_runtime():

    runtime = RASERuntime()

    runtime.register_agent(
        "A1",
        "VisitAnalysis",
        "AnalyzeVisit"
    )

    runtime.register_agent(
        "A2",
        "VetAssignment",
        "AssignVet"
    )

    runtime.register_agent(
        "A3",
        "AssignmentVerification",
        "VerifyAssignment"
    )

    runtime.register_agent(
        "A2_prime",
        "VetAssignment",
        "AssignVet"
    )

    # Original architecture

    runtime.add_dependency(
        "A1",
        "A2",
        "produces-event",
        propagation_weight=0.90
    )

    runtime.add_dependency(
        "A2",
        "A3",
        "produces-result",
        propagation_weight=0.80
    )

    # Initial evidence

    runtime.add_evidence(
        "A1",
        "VisitAnalysis",
        "SUCCESS",
        1.0
    )

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0
    )

    runtime.add_evidence(
        "A3",
        "AssignmentVerification",
        "SUCCESS",
        1.0
    )

    runtime.add_evidence(
        "A2_prime",
        "VetAssignment",
        "SUCCESS",
        1.0
    )

    return runtime


# =========================================================
# Create agents
# =========================================================

def create_agents(scenario):

    a1 = VisitAnalysisAgent()

    a2 = VetAssignmentAgent(
        agent_id="A2"
    )

    # -----------------------------------------------------
    # Replacement behavior
    # -----------------------------------------------------

    if scenario in {
        "S3_PASS",
        "S1_UNAVAILABLE"
    }:
        a2_prime = VetAssignmentAgent(
            agent_id="A2_prime"
        )

    else:
        a2_prime = VetAssignmentAgent(
            agent_id="A2_prime",
            degraded=True
        )

    a3 = VerificationAgent()

    return a1, a2, a2_prime, a3


# =========================================================
# Execute one experiment
# =========================================================

def run_one(scenario, repetition):

    seed = 1000 + repetition

    random.seed(seed)

    runtime = create_runtime()

    a1, a2, a2_prime, a3 = create_agents(
        scenario
    )

    # -----------------------------------------------------
    # Input
    # -----------------------------------------------------

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05"
    }

    # -----------------------------------------------------
    # Step 1: Normal analysis
    # -----------------------------------------------------

    analysis_result = a1.analyze(
        visit_request
    )

    if not analysis_result.success:

        return {
            "scenario": scenario,
            "repetition": repetition,
            "seed": seed,
            "decision": "ANALYSIS_FAILURE"
        }

    # -----------------------------------------------------
    # Baseline evidence
    # -----------------------------------------------------

    runtime.add_evidence(
        "A1",
        "VisitAnalysis",
        "SUCCESS",
        1.0
    )

    # -----------------------------------------------------
    # S0: Normal operation
    # -----------------------------------------------------

    if scenario == "S0_NORMAL":

        start = now_ms()

        assignment_result = a2.assign(
            analysis_result.output
        )

        verification_result = a3.verify(
            assignment_result.output
        )

        total_latency = now_ms() - start

        return {
            "scenario": scenario,
            "repetition": repetition,
            "seed": seed,
            "failed_agent": "",
            "replacement_agent": "",
            "impact_a2": 0.0,
            "impact_a3": 0.0,
            "assurance_a2_before": runtime.get_assurance(
                "A2",
                "VetAssignment"
            ),
            "assurance_replacement_after": "",
            "reconfiguration_count": 0,
            "execution_success": assignment_result.success,
            "verification_success": verification_result.success,
            "decision": "NO_ADAPTATION",
            "rollback": False,
            "analysis_latency_ms": 0.0,
            "adaptation_latency_ms": 0.0,
            "verification_latency_ms": total_latency,
            "total_latency_ms": total_latency
        }

    # -----------------------------------------------------
    # Failure scenarios
    # -----------------------------------------------------

    runtime.record_agent_failure(
        "A2",
        "VetAssignment"
    )

    assurance_before = runtime.get_assurance(
        "A2",
        "VetAssignment"
    )

    # -----------------------------------------------------
    # Typed impact analysis
    # -----------------------------------------------------

    start_analysis = now_ms()

    impact = runtime.analyze_impact(
        "A2"
    )

    analysis_latency = (
        now_ms() - start_analysis
    )

    impact_a2 = impact.get(
        "A2",
        0.0
    )

    impact_a3 = impact.get(
        "A3",
        0.0
    )

    # -----------------------------------------------------
    # Alternative discovery
    # -----------------------------------------------------

    replacement = runtime.find_alternative_agent(
        capability="VetAssignment",
        responsibility="AssignVet",
        excluded_agent="A2"
    )

    # -----------------------------------------------------
    # S1: unavailable agent with no actual replacement
    #
    # We deliberately test the architecture response.
    # The replacement exists in the runtime model, so
    # RASE should be able to discover it.
    # -----------------------------------------------------

    start_adaptation = now_ms()

    if replacement is None:

        return {
            "scenario": scenario,
            "repetition": repetition,
            "seed": seed,
            "failed_agent": "A2",
            "replacement_agent": "",
            "impact_a2": impact_a2,
            "impact_a3": impact_a3,
            "assurance_a2_before": assurance_before,
            "assurance_replacement_after": "",
            "reconfiguration_count": 0,
            "execution_success": False,
            "verification_success": False,
            "decision": "NO_REPLACEMENT",
            "rollback": False,
            "analysis_latency_ms": analysis_latency,
            "adaptation_latency_ms": 0.0,
            "verification_latency_ms": 0.0,
            "total_latency_ms": analysis_latency
        }

    # -----------------------------------------------------
    # Reconfigure
    # -----------------------------------------------------

    transitions = runtime.reconfigure_dependency(
        "A2",
        replacement
    )

    adaptation_latency = (
        now_ms() - start_adaptation
    )

    # -----------------------------------------------------
    # S2: degraded replacement
    # S3_PASS: successful replacement
    # S4_FAIL: failed replacement
    # -----------------------------------------------------

    start_verification = now_ms()

    if scenario == "S2_DEGRADED":

        # Explicitly make the replacement degraded.
        a2_prime.degraded = True

    elif scenario == "S4_FAIL":

        # Explicitly make the replacement fail.
        a2_prime.degraded = True

    else:

        a2_prime.degraded = False

    replacement_result = a2_prime.assign(
        analysis_result.output
    )

    verification_result = a3.verify(
        replacement_result.output
    )

    verification_latency = (
        now_ms() - start_verification
    )

    # -----------------------------------------------------
    # Verification decision
    # -----------------------------------------------------

    if verification_result.success:

        decision = "COMMIT"

        rollback = False

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0
        )

    else:

        decision = "ROLLBACK"

        rollback = True

        runtime.record_verification_failure(
            "A2_prime",
            "VetAssignment"
        )

        runtime.rollback_reconfiguration(
            transitions,
            replacement
        )

    assurance_replacement_after = (
        runtime.get_assurance(
            "A2_prime",
            "VetAssignment"
        )
    )

    total_latency = (
        analysis_latency
        + adaptation_latency
        + verification_latency
    )

    # -----------------------------------------------------
    # Return experiment record
    # -----------------------------------------------------

    return {
        "scenario": scenario,
        "repetition": repetition,
        "seed": seed,
        "failed_agent": "A2",
        "replacement_agent": replacement,
        "impact_a2": impact_a2,
        "impact_a3": impact_a3,
        "assurance_a2_before": assurance_before,
        "assurance_replacement_after": assurance_replacement_after,
        "reconfiguration_count": len(
            transitions
        ),
        "execution_success": replacement_result.success,
        "verification_success": verification_result.success,
        "decision": decision,
        "rollback": rollback,
        "analysis_latency_ms": analysis_latency,
        "adaptation_latency_ms": adaptation_latency,
        "verification_latency_ms": verification_latency,
        "total_latency_ms": total_latency
    }


# =========================================================
# Main experiment
# =========================================================

def main():

    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_results = []

    print()
    print("=" * 70)
    print("RASE PILOT EXPERIMENT")
    print("=" * 70)

    print(
        f"Scenarios: {len(SCENARIOS)}"
    )

    print(
        f"Repetitions per scenario: {REPETITIONS}"
    )

    print(
        f"Total runs: "
        f"{len(SCENARIOS) * REPETITIONS}"
    )

    print()

    # -----------------------------------------------------
    # Run experiments
    # -----------------------------------------------------

    for scenario in SCENARIOS:

        print(
            f"\nRunning {scenario}..."
        )

        for repetition in range(
            1,
            REPETITIONS + 1
        ):

            result = run_one(
                scenario,
                repetition
            )

            all_results.append(
                result
            )

            print(
                f"  Run {repetition:02d}: "
                f"{result.get('decision', '')}"
            )

    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

    fieldnames = sorted(
        {
            key
            for result in all_results
            for key in result.keys()
        }
    )

    with open(
        RESULTS_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            all_results
        )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("EXPERIMENT COMPLETE")
    print("=" * 70)

    print(
        f"Results saved to:\n"
        f"{RESULTS_FILE}"
    )

    print()

    for scenario in SCENARIOS:

        scenario_results = [
            result
            for result in all_results
            if result["scenario"] == scenario
        ]

        commits = sum(
            1
            for result in scenario_results
            if result.get("decision") == "COMMIT"
        )

        rollbacks = sum(
            1
            for result in scenario_results
            if result.get("decision") == "ROLLBACK"
        )

        print(
            f"{scenario}: "
            f"{len(scenario_results)} runs | "
            f"commit={commits} | "
            f"rollback={rollbacks}"
        )


if __name__ == "__main__":
    main()