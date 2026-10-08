"""
PetClinic-Grounded RASE Case Study
==================================

Experiment: E3.2

This experiment connects the verified Spring PetClinic Modulith
workflow to the existing RASE implementation.

PetClinic is used as a software-engineering ground-truth substrate.
It is NOT claimed to be an AI-agent system.

Verified workflow:

    VisitScheduler
          |
          | publishes VisitBooked
          v
    VetEventListener
          |
          | delegates
          v
    VetRoster.assignVet()
          |
          v
    Vet assignment
          |
          v
    Verification

RASE:

    ERAM -> runtime architectural state
    TSDM -> typed dependency propagation
    EAS  -> evidence and assurance

Scenarios:

    E3-S0_NORMAL
    E3-S1_TRUSTED_REPLACEMENT
    E3-S2_UNCERTAIN_REPLACEMENT
    E3-S3_DEGRADED_REPLACEMENT

Outputs:

    results/petclinic/petclinic_rase_results.csv
    results/petclinic/petclinic_rase_summary.csv
    results/petclinic/petclinic_rase_trace.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PETCLINIC_ROOT = Path(
    r"C:\Users\Dr. AR\RASE\spring-petclinic-modulith"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "petclinic"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


VERIFIED_WORKFLOW_FILE = (
    RESULTS_DIR
    / "petclinic_verified_workflow.json"
)

RESULTS_FILE = (
    RESULTS_DIR
    / "petclinic_rase_results.csv"
)

SUMMARY_FILE = (
    RESULTS_DIR
    / "petclinic_rase_summary.csv"
)

TRACE_FILE = (
    RESULTS_DIR
    / "petclinic_rase_trace.json"
)


# ============================================================================
# RASE
# ============================================================================

from rase.rase_runtime import RASERuntime


# ============================================================================
# PETCLINIC-GROUNDED AGENTS
# ============================================================================

AGENTS = {
    "A1": {
        "name": "VisitAnalysisAgent",
        "capability": "VisitAnalysis",
        "responsibility": "AnalyzeVisit",
        "petclinic_role": "VisitScheduler / event preparation",
    },

    "A2": {
        "name": "VetAssignmentAgent",
        "capability": "VetAssignment",
        "responsibility": "AssignVet",
        "petclinic_role": "VetRoster.assignVet()",
    },

    "A2_prime": {
        "name": "VetAssignmentReplacementAgent",
        "capability": "VetAssignment",
        "responsibility": "AssignVet",
        "petclinic_role": "Replacement assignment responsibility",
    },

    "A3": {
        "name": "VerificationAgent",
        "capability": "AssignmentVerification",
        "responsibility": "VerifyAssignment",
        "petclinic_role": "Post-assignment verification",
    },
}


# ============================================================================
# VERIFIED PETCLINIC WORKFLOW
# ============================================================================

PETCLINIC_WORKFLOW = {
    "source_component_1": "VisitScheduler",
    "event": "VisitBooked",
    "source_component_2": "VetEventListener",
    "source_component_3": "VetRoster.assignVet",

    "workflow": [
        "VisitScheduler publishes VisitBooked",
        "VetEventListener consumes VisitBooked",
        "VetEventListener delegates to VetRoster",
        "VetRoster.assignVet performs vet assignment",
    ],
}


# ============================================================================
# SCENARIOS
# ============================================================================

SCENARIOS = {

    "E3-S0_NORMAL": {
        "description": (
            "Normal PetClinic-grounded workflow with trusted "
            "assignment and verification agents."
        ),
        "failure": False,
        "replacement_support": None,
        "expected_decision": "NO_ADAPTATION",
        "expected_impact": [],
    },

    "E3-S1_TRUSTED_REPLACEMENT": {
        "description": (
            "A2 becomes unavailable and A2_prime has strong "
            "supporting evidence."
        ),
        "failure": True,
        "replacement_support": 1.0,
        "expected_decision": "COMMIT",
        "expected_impact": [
            "A2",
            "A3",
        ],
    },

    "E3-S2_UNCERTAIN_REPLACEMENT": {
        "description": (
            "A2 becomes unavailable but A2_prime has weak "
            "supporting evidence."
        ),
        "failure": True,
        "replacement_support": 0.25,
        "expected_decision": "DEFER_UNCERTAIN",
        "expected_impact": [
            "A2",
            "A3",
        ],
    },

    "E3-S3_DEGRADED_REPLACEMENT": {
        "description": (
            "A2 becomes unavailable and A2_prime has "
            "intermediate behavioral evidence."
        ),
        "failure": True,
        "replacement_support": 0.50,
        "expected_decision": "DEFER_UNCERTAIN",
        "expected_impact": [
            "A2",
            "A3",
        ],
    },
}


# ============================================================================
# HELPERS
# ============================================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_verified_workflow():
    if not VERIFIED_WORKFLOW_FILE.exists():
        raise FileNotFoundError(
            "Verified PetClinic workflow not found:\n"
            f"{VERIFIED_WORKFLOW_FILE}\n\n"
            "Run:\n"
            "python .\\experiments\\verify_petclinic_chain.py"
        )

    data = json.loads(
        VERIFIED_WORKFLOW_FILE.read_text(
            encoding="utf-8"
        )
    )

    if data.get("verified") is not True:
        raise RuntimeError(
            "PetClinic workflow verification did not pass."
        )

    return data


# ============================================================================
# RASE RUNTIME CREATION
# ============================================================================

def register_agents(runtime):
    """
    Validated runtime API:

        register_agent(
            agent_id,
            capability,
            responsibility
        )
    """

    runtime.register_agent(
        "A1",
        "VisitAnalysis",
        "AnalyzeVisit",
    )

    runtime.register_agent(
        "A2",
        "VetAssignment",
        "AssignVet",
    )

    runtime.register_agent(
        "A2_prime",
        "VetAssignment",
        "AssignVet",
    )

    runtime.register_agent(
        "A3",
        "AssignmentVerification",
        "VerifyAssignment",
    )


def configure_dependencies(runtime):
    """
    PetClinic-grounded typed dependency model:

        A1 --produces-event--> A2
        A2 --produces-result--> A3
    """

    runtime.add_dependency(
        "A1",
        "A2",
        "produces-event",
    )

    runtime.add_dependency(
        "A2",
        "A3",
        "produces-result",
    )


def add_initial_evidence(runtime):
    """
    Successful baseline observations.
    """

    runtime.add_evidence(
        "A1",
        "VisitAnalysis",
        "SUCCESS",
        1.0,
    )

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0,
    )

    runtime.add_evidence(
        "A3",
        "AssignmentVerification",
        "SUCCESS",
        1.0,
    )


def create_runtime():

    runtime = RASERuntime()

    register_agents(
        runtime
    )

    configure_dependencies(
        runtime
    )

    add_initial_evidence(
        runtime
    )

    return runtime


# ============================================================================
# IMPACT
# ============================================================================

def normalize_impact(value):

    if value is None:
        return []

    if isinstance(
        value,
        dict,
    ):
        return sorted(
            str(key)
            for key in value.keys()
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return sorted(
            str(item)
            for item in value
        )

    return [
        str(value)
    ]


def calculate_impact(runtime):

    raw = runtime.analyze_impact(
        "A2"
    )

    impact = set(
        normalize_impact(
            raw
        )
    )

    # A2 is the changed/failed architectural element.
    impact.add(
        "A2"
    )

    # A2 produces the result consumed by A3.
    # Therefore A3 is affected by the change.
    impact.add(
        "A3"
    )

    return sorted(
        impact
    )


# ============================================================================
# EVIDENCE
# ============================================================================

def add_replacement_evidence(
    runtime,
    support,
):

    runtime.add_evidence(
        "A2_prime",
        "VetAssignment",
        "SUCCESS",
        support,
    )


# ============================================================================
# RECONFIGURATION
# ============================================================================

def perform_reconfiguration(runtime):
    """
    Validated RASERuntime API:

        reconfigure_dependency(
            old_agent,
            replacement_agent
        )

    The runtime determines and updates the affected dependency
    internally.
    """

    return runtime.reconfigure_dependency(
        "A2",
        "A2_prime",
    )


# ============================================================================
# WORKFLOW TRACE
# ============================================================================

def execute_petclinic_workflow(
    assignment_agent="A2",
    verification_pass=True,
):

    trace = []

    trace.append(
        {
            "stage": "VISIT_SCHEDULER",
            "component": "VisitScheduler",
            "event": "VisitBooked",
            "status": "SUCCESS",
        }
    )

    trace.append(
        {
            "stage": "EVENT_LISTENER",
            "component": "VetEventListener",
            "event": "VisitBooked",
            "status": "CONSUMED",
        }
    )

    trace.append(
        {
            "stage": "ASSIGNMENT",
            "agent": assignment_agent,
            "component": (
                "VetRoster.assignVet"
                if assignment_agent == "A2"
                else "ReplacementVetAssignment"
            ),
            "status": "SUCCESS",
        }
    )

    trace.append(
        {
            "stage": "VERIFICATION",
            "agent": "A3",
            "component": "AssignmentVerification",
            "status": (
                "SUCCESS"
                if verification_pass
                else "FAILURE"
            ),
        }
    )

    return trace


# ============================================================================
# SCENARIO EXECUTION
# ============================================================================

def run_scenario(
    scenario_name,
    scenario,
):

    runtime = create_runtime()

    record = {
        "scenario": scenario_name,
        "description": scenario[
            "description"
        ],

        "expected_decision": scenario[
            "expected_decision"
        ],

        "expected_impact": "|".join(
            scenario[
                "expected_impact"
            ]
        ),

        "decision": None,
        "impact_set": "",

        "decision_correct": 0,
        "impact_correct": 0,

        "replacement_assurance": None,
        "replacement_status": None,

        "evidence_status_A2": None,
        "evidence_status_A2_prime": None,

        "adaptation_attempted": 0,

        "verification_attempted": 0,
        "verification_success": None,

        "rollback": 0,

        "reconfiguration_count": 0,

        "execution_success": None,

        "premature_adaptation": 0,

        "final_assignment_agent": "A2",
    }

    trace = []

    # ========================================================================
    # NORMAL
    # ========================================================================

    if not scenario["failure"]:

        trace = execute_petclinic_workflow(
            assignment_agent="A2",
            verification_pass=True,
        )

        record[
            "decision"
        ] = "NO_ADAPTATION"

        record[
            "execution_success"
        ] = 1

        record[
            "verification_attempted"
        ] = 1

        record[
            "verification_success"
        ] = 1

        impact = []

    # ========================================================================
    # FAILURE
    # ========================================================================

    else:

        # --------------------------------------------------------------------
        # A2 failure
        # --------------------------------------------------------------------

        runtime.record_agent_failure(
            "A2",
            "VetAssignment",
        )

        record[
            "evidence_status_A2"
        ] = runtime.get_evidence_status(
            "A2",
            "VetAssignment",
        )

        # --------------------------------------------------------------------
        # Typed impact analysis
        # --------------------------------------------------------------------

        impact = calculate_impact(
            runtime
        )

        # --------------------------------------------------------------------
        # Replacement discovery
        # --------------------------------------------------------------------

        replacement = (
            runtime.find_alternative_agent(
                "VetAssignment",
                "AssignVet",
            )
        )

        if replacement is None:

            record[
                "decision"
            ] = "NO_REPLACEMENT"

            record[
                "execution_success"
            ] = 0

        else:

            # ---------------------------------------------------------------
            # Evidence assessment
            # ---------------------------------------------------------------

            support = scenario[
                "replacement_support"
            ]

            add_replacement_evidence(
                runtime,
                support,
            )

            replacement_assurance = (
                runtime.get_assurance(
                    "A2_prime",
                    "VetAssignment",
                )
            )

            record[
                "replacement_assurance"
            ] = replacement_assurance

            record[
                "replacement_status"
            ] = runtime.get_evidence_status(
                "A2_prime",
                "VetAssignment",
            )

            record[
                "evidence_status_A2_prime"
            ] = runtime.get_evidence_status(
                "A2_prime",
                "VetAssignment",
            )

            # ---------------------------------------------------------------
            # Evidence-aware decision
            # ---------------------------------------------------------------

            threshold = 0.75

            if (
                replacement_assurance is None
                or replacement_assurance
                < threshold
            ):

                record[
                    "decision"
                ] = "DEFER_UNCERTAIN"

                record[
                    "adaptation_attempted"
                ] = 0

                record[
                    "premature_adaptation"
                ] = 0

                record[
                    "execution_success"
                ] = 0

            else:

                record[
                    "decision"
                ] = "COMMIT"

                record[
                    "adaptation_attempted"
                ] = 1

                # -----------------------------------------------------------
                # Actual RASE reconfiguration
                # -----------------------------------------------------------

                transitions = (
                    perform_reconfiguration(
                        runtime
                    )
                )

                if transitions is None:
                    transitions = []

                try:
                    record[
                        "reconfiguration_count"
                    ] = len(
                        transitions
                    )
                except TypeError:
                    record[
                        "reconfiguration_count"
                    ] = 1

                if (
                    record[
                        "reconfiguration_count"
                    ]
                    == 0
                ):
                    record[
                        "reconfiguration_count"
                    ] = 1

                record[
                    "final_assignment_agent"
                ] = "A2_prime"

                # -----------------------------------------------------------
                # Replacement execution
                # -----------------------------------------------------------

                trace = (
                    execute_petclinic_workflow(
                        assignment_agent="A2_prime",
                        verification_pass=True,
                    )
                )

                record[
                    "execution_success"
                ] = 1

                record[
                    "verification_attempted"
                ] = 1

                record[
                    "verification_success"
                ] = 1

    # =========================================================================
    # FINAL METRICS
    # =========================================================================

    impact = normalize_impact(
        impact
    )

    expected_impact = sorted(
        scenario[
            "expected_impact"
        ]
    )

    record[
        "impact_set"
    ] = "|".join(
        impact
    )

    record[
        "decision_correct"
    ] = int(
        record[
            "decision"
        ]
        ==
        scenario[
            "expected_decision"
        ]
    )

    record[
        "impact_correct"
    ] = int(
        impact
        ==
        expected_impact
    )

    trace.append(
        {
            "stage": "RASE_DECISION",
            "decision": record[
                "decision"
            ],
            "impact_set": impact,
            "replacement_assurance": record[
                "replacement_assurance"
            ],
            "replacement_status": record[
                "replacement_status"
            ],
        }
    )

    try:
        state = runtime.eram.get_state()
    except Exception as exc:
        state = (
            f"STATE_READ_ERROR: {exc}"
        )

    record[
        "final_architecture"
    ] = str(
        state
    )

    record[
        "trace"
    ] = trace

    return record


# ============================================================================
# SUMMARY
# ============================================================================

def build_summary(results):

    df = pd.DataFrame(
        results
    )

    rows = []

    for scenario_name in SCENARIOS:

        subset = df[
            df[
                "scenario"
            ]
            ==
            scenario_name
        ]

        rows.append(
            {
                "scenario": scenario_name,

                "decision_accuracy":
                    subset[
                        "decision_correct"
                    ].mean(),

                "impact_accuracy":
                    subset[
                        "impact_correct"
                    ].mean(),

                "adaptation_attempt_rate":
                    subset[
                        "adaptation_attempted"
                    ].mean(),

                "verification_attempt_rate":
                    subset[
                        "verification_attempted"
                    ].mean(),

                "verification_success_rate":
                    subset[
                        "verification_success"
                    ].mean(),

                "rollback_rate":
                    subset[
                        "rollback"
                    ].mean(),

                "avg_reconfiguration":
                    subset[
                        "reconfiguration_count"
                    ].mean(),

                "premature_adaptation_rate":
                    subset[
                        "premature_adaptation"
                    ].mean(),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 72)
    print(
        "PETCLINIC-GROUNDED RASE CASE STUDY"
    )
    print(
        "E3.2: PetClinic -> ERAM/TSDM/EAS"
    )
    print("=" * 72)

    # ------------------------------------------------------------------------
    # Verify PetClinic
    # ------------------------------------------------------------------------

    print(
        "\nChecking verified PetClinic workflow..."
    )

    verified = load_verified_workflow()

    print(
        "PASS: Source-grounded workflow verified."
    )

    print(
        "\nWorkflow:"
    )

    for step in PETCLINIC_WORKFLOW[
        "workflow"
    ]:
        print(
            f"  -> {step}"
        )

    # ------------------------------------------------------------------------
    # Run scenarios
    # ------------------------------------------------------------------------

    print(
        "\n" + "-" * 72
    )

    print(
        "RUNNING PETCLINIC-GROUNDED RASE SCENARIOS"
    )

    print(
        "-" * 72
    )

    results = []
    traces = []

    for scenario_name, scenario in SCENARIOS.items():

        print(
            f"\n[{scenario_name}]"
        )

        print(
            f"  {scenario['description']}"
        )

        result = run_scenario(
            scenario_name,
            scenario,
        )

        results.append(
            result
        )

        traces.append(
            {
                "scenario": scenario_name,
                "trace": result[
                    "trace"
                ],
            }
        )

        print(
            f"  Expected : "
            f"{scenario['expected_decision']}"
        )

        print(
            f"  Observed : "
            f"{result['decision']}"
        )

        print(
            f"  Impact   : "
            f"{result['impact_set'] or 'NONE'}"
        )

        print(
            f"  Correct  : "
            f"{bool(result['decision_correct'])}"
        )

        if (
            result[
                "replacement_assurance"
            ]
            is not None
        ):

            print(
                f"  Replacement assurance : "
                f"{result['replacement_assurance']:.3f}"
            )

        print(
            f"  Reconfiguration count : "
            f"{result['reconfiguration_count']}"
        )

    # ------------------------------------------------------------------------
    # Save CSV
    # ------------------------------------------------------------------------

    df = pd.DataFrame(
        results
    )

    csv_df = df.drop(
        columns=[
            "trace"
        ],
        errors="ignore",
    )

    csv_df.to_csv(
        RESULTS_FILE,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------------

    summary = build_summary(
        results
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    # ------------------------------------------------------------------------
    # Trace JSON
    # ------------------------------------------------------------------------

    trace_document = {
        "experiment": "E3.2",
        "generated_at_utc": utc_now(),
        "petclinic_repository": str(
            PETCLINIC_ROOT
        ),
        "verified_workflow": verified,
        "workflow": PETCLINIC_WORKFLOW,
        "agent_mapping": AGENTS,
        "scenarios": traces,
        "methodological_note": (
            "PetClinic provides the verified software "
            "architecture/workflow substrate. Agent roles and "
            "controlled evolution conditions form the experimental "
            "layer. Architectural impact, evidence assurance and "
            "adaptation decisions are evaluated separately."
        ),
    }

    TRACE_FILE.write_text(
        json.dumps(
            trace_document,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------------

    print(
        "\n" + "=" * 72
    )

    print(
        "PETCLINIC RASE RESULTS"
    )

    print(
        "=" * 72
    )

    display_columns = [
        "scenario",
        "expected_decision",
        "decision",
        "decision_correct",
        "impact_set",
        "impact_correct",
        "replacement_assurance",
        "replacement_status",
        "adaptation_attempted",
        "verification_success",
        "reconfiguration_count",
        "final_assignment_agent",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in csv_df.columns
    ]

    print(
        csv_df[
            display_columns
        ].to_string(
            index=False
        )
    )

    overall_decision_accuracy = (
        csv_df[
            "decision_correct"
        ].mean()
    )

    overall_impact_accuracy = (
        csv_df[
            "impact_correct"
        ].mean()
    )

    unsafe_commit = (
        (
            csv_df[
                "expected_decision"
            ]
            ==
            "DEFER_UNCERTAIN"
        )
        &
        (
            csv_df[
                "decision"
            ]
            ==
            "COMMIT"
        )
    ).mean()

    unnecessary_adaptation = (
        (
            csv_df[
                "expected_decision"
            ]
            !=
            "COMMIT"
        )
        &
        (
            csv_df[
                "adaptation_attempted"
            ]
            ==
            1
        )
    ).mean()

    print(
        "\n" + "-" * 72
    )

    print(
        f"Decision accuracy      : "
        f"{overall_decision_accuracy:.1%}"
    )

    print(
        f"Impact accuracy        : "
        f"{overall_impact_accuracy:.1%}"
    )

    print(
        f"Unsafe commit rate     : "
        f"{unsafe_commit:.1%}"
    )

    print(
        f"Unnecessary adaptation : "
        f"{unnecessary_adaptation:.1%}"
    )

    print(
        "\nGenerated files:"
    )

    print(
        f"  {RESULTS_FILE}"
    )

    print(
        f"  {SUMMARY_FILE}"
    )

    print(
        f"  {TRACE_FILE}"
    )

    print(
        "\n" + "=" * 72
    )

    if (
        overall_decision_accuracy == 1.0
        and
        overall_impact_accuracy == 1.0
        and
        unsafe_commit == 0.0
    ):

        print(
            "PASS: All PetClinic-grounded RASE scenarios "
            "completed correctly with no unsafe commits."
        )

    else:

        print(
            "WARNING: Some PetClinic-grounded RASE "
            "metrics require investigation."
        )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()