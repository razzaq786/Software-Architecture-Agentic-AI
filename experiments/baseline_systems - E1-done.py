import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.agents import (
    VisitAnalysisAgent,
    VetAssignmentAgent,
    VerificationAgent,
)

from rase.rase_runtime import RASERuntime


# =====================================================================
# AGENT CREATION
# =====================================================================

def create_agents(include_replacement=True, degraded_replacement=False):
    """
    Create the common agents used by all baseline systems.

    A1:
        Visit Analysis Agent

    A2:
        Primary Veterinarian Assignment Agent

    A2_prime:
        Optional replacement Veterinarian Assignment Agent

    A3:
        Independent Verification Agent

    A4:
        Independent observational branch used for testing
        typed impact propagation.
    """

    a1 = VisitAnalysisAgent()

    a2 = VetAssignmentAgent(
        agent_id="A2",
        available=True,
        degraded=False,
    )

    if include_replacement:
        a2_prime = VetAssignmentAgent(
            agent_id="A2_prime",
            available=True,
            degraded=degraded_replacement,
        )
    else:
        a2_prime = None

    a3 = VerificationAgent()

    # Independent branch used to test typed impact propagation.
    a4 = VetAssignmentAgent(
        agent_id="A4",
        available=True,
        degraded=False,
    )

    return a1, a2, a2_prime, a3, a4


# =====================================================================
# ARCHITECTURE REPRESENTATION
# =====================================================================

def architecture_string(runtime):
    """
    Return the currently active dependency structure
    in a deterministic textual form.
    """

    state = runtime.eram.get_state()

    dependencies = sorted(
        state["dependencies"],
        key=lambda x: (
            x["source"],
            x["target"],
            x["relation_type"],
        ),
    )

    if not dependencies:
        return "EMPTY"

    return "|".join(
        f'{d["source"]}->{d["target"]}'
        for d in dependencies
    )


# =====================================================================
# RASE RUNTIME CREATION
# =====================================================================

def create_rase_runtime():
    """
    Create the common architectural environment.

    The S4 branch introduces A4 as an observationally connected
    agent. The 'observes' relationship is intentionally
    non-propagating in TSDM, allowing the experiment to
    distinguish semantic dependency propagation from generic
    graph connectivity.
    """

    runtime = RASERuntime()

    # ---------------------------------------------------------
    # Register agents.
    # ---------------------------------------------------------

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
        "A3",
        "AssignmentVerification",
        "VerifyAssignment",
    )

    runtime.register_agent(
        "A2_prime",
        "VetAssignment",
        "AssignVet",
    )

    runtime.register_agent(
        "A4",
        "NotificationObservation",
        "ObserveAssignment",
    )

    # ---------------------------------------------------------
    # Core workflow dependencies.
    # ---------------------------------------------------------

    runtime.add_dependency(
        "A1",
        "A2",
        "produces-event",
        propagation_weight=0.90,
    )

    runtime.add_dependency(
        "A2",
        "A3",
        "produces-result",
        propagation_weight=0.80,
    )

    # ---------------------------------------------------------
    # Observational relationship.
    #
    # This represents architectural connectivity but should NOT
    # propagate an A2 failure to A4 in the typed model.
    # ---------------------------------------------------------

    runtime.add_dependency(
        "A4",
        "A2",
        "observes",
        propagation_weight=0.00,
    )

    # ---------------------------------------------------------
    # Initial evidence.
    # ---------------------------------------------------------

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

    runtime.add_evidence(
        "A2_prime",
        "VetAssignment",
        "SUCCESS",
        1.0,
    )

    runtime.add_evidence(
        "A4",
        "NotificationObservation",
        "SUCCESS",
        1.0,
    )

    return runtime


# =====================================================================
# COMMON NORMAL WORKFLOW
# =====================================================================

def execute_normal_workflow(a1, a2, a3):
    """
    Execute the normal:

        Visit -> Assignment -> Verification

    workflow.
    """

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    analysis = a1.analyze(visit_request)

    if not analysis.success:
        return {
            "execution_success": False,
            "verification_success": False,
            "assignment_result": None,
            "verification_result": None,
        }

    assignment = a2.assign(
        analysis.output
    )

    if not assignment.success:
        return {
            "execution_success": False,
            "verification_success": False,
            "assignment_result": assignment,
            "verification_result": None,
        }

    verification = a3.verify(
        assignment.output
    )

    return {
        "execution_success": assignment.success,
        "verification_success": verification.success,
        "assignment_result": assignment,
        "verification_result": verification,
    }


# =====================================================================
# B1 - STATIC
# =====================================================================

def run_static(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B1: Static orchestration.

    The workflow is fixed as:

        A1 -> A2 -> A3

    No replacement discovery and no architectural adaptation.
    """

    if scenario == "S0_NORMAL":

        result = execute_normal_workflow(
            a1,
            a2,
            a3,
        )

        return {
            "system": "B1_STATIC",
            "decision": "NO_ADAPTATION",
            "execution_success": result["execution_success"],
            "verification_success": result["verification_success"],
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    return {
        "system": "B1_STATIC",
        "decision": "FAIL",
        "execution_success": False,
        "verification_success": False,
        "reconfiguration_count": 0,
        "rollback": False,
        "final_architecture": "A1->A2->A3",
        "impact_set": [],
    }


# =====================================================================
# B2 - DYNAMIC
# =====================================================================

def run_dynamic(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B2: Dynamic orchestration.

    The orchestrator discovers a replacement when one exists.

    It does not maintain:
        - an explicit runtime architectural state,
        - typed semantic dependencies,
        - evidence-assessed architectural state.
    """

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    analysis = a1.analyze(
        visit_request
    )

    if not analysis.success:

        return {
            "system": "B2_DYNAMIC",
            "decision": "FAIL",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Normal execution.
    # ---------------------------------------------------------

    if scenario == "S0_NORMAL":

        assignment = a2.assign(
            analysis.output
        )

        verification = a3.verify(
            assignment.output
        )

        return {
            "system": "B2_DYNAMIC",
            "decision": "NO_ADAPTATION",
            "execution_success": assignment.success,
            "verification_success": verification.success,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # A2 fails.
    # ---------------------------------------------------------

    a2.available = False

    # ---------------------------------------------------------
    # No replacement.
    # ---------------------------------------------------------

    if a2_prime is None:

        return {
            "system": "B2_DYNAMIC",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # ---------------------------------------------------------
    # Replacement execution.
    # ---------------------------------------------------------

    replacement = a2_prime.assign(
        analysis.output
    )

    verification = a3.verify(
        replacement.output
    )

    if replacement.success and verification.success:

        decision = "COMMIT"
        rollback = False
        final_architecture = "A1->A2_prime->A3"

    else:

        decision = "ROLLBACK"
        rollback = True
        final_architecture = "A1->A2->A3"

    return {
        "system": "B2_DYNAMIC",
        "decision": decision,
        "execution_success": replacement.success,
        "verification_success": verification.success,
        "reconfiguration_count": 2,
        "rollback": rollback,
        "final_architecture": final_architecture,
        "impact_set": ["A2", "A3"],
    }


# =====================================================================
# B3 - UNTYPED
# =====================================================================

def run_untyped(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B3: Untyped dependency graph.

    The system represents connectivity but does not distinguish
    semantic dependency types.

    Therefore, in S4, the connection between A2 and A4 is
    conservatively treated as potentially affected by an A2
    failure.
    """

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    analysis = a1.analyze(
        visit_request
    )

    if not analysis.success:

        return {
            "system": "B3_UNTYPED",
            "decision": "FAIL",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Normal execution.
    # ---------------------------------------------------------

    if scenario == "S0_NORMAL":

        assignment = a2.assign(
            analysis.output
        )

        verification = a3.verify(
            assignment.output
        )

        return {
            "system": "B3_UNTYPED",
            "decision": "NO_ADAPTATION",
            "execution_success": assignment.success,
            "verification_success": verification.success,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # S4 tests the difference between an untyped connectivity
    # graph and typed semantic dependencies.
    # ---------------------------------------------------------

    if scenario == "S4_IRRELEVANT_BRANCH":

        return {
            "system": "B3_UNTYPED",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3|A4->A2",
            "impact_set": ["A2", "A3", "A4"],
        }

    # ---------------------------------------------------------
    # No replacement available.
    # ---------------------------------------------------------

    if a2_prime is None:

        return {
            "system": "B3_UNTYPED",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # ---------------------------------------------------------
    # Replacement.
    # ---------------------------------------------------------

    replacement = a2_prime.assign(
        analysis.output
    )

    verification = a3.verify(
        replacement.output
    )

    if replacement.success and verification.success:

        return {
            "system": "B3_UNTYPED",
            "decision": "COMMIT",
            "execution_success": True,
            "verification_success": True,
            "reconfiguration_count": 2,
            "rollback": False,
            "final_architecture": "A1->A2_prime->A3",
            "impact_set": ["A2", "A3"],
        }

    return {
        "system": "B3_UNTYPED",
        "decision": "ROLLBACK",
        "execution_success": False,
        "verification_success": False,
        "reconfiguration_count": 2,
        "rollback": True,
        "final_architecture": "A1->A2->A3",
        "impact_set": ["A2", "A3"],
    }


# =====================================================================
# B4 - RASE WITHOUT EAS
# =====================================================================

def run_rase_no_eas(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B4: RASE without Evidence-Assessed State (EAS).

    Uses:
        - ERAM
        - typed dependencies
        - impact analysis
        - architectural reconfiguration
        - independent verification
        - rollback

    Does not use:
        - EAS assurance gating
        - uncertainty-based adaptation deferral

    This isolates the contribution of EAS.
    """

    runtime = create_rase_runtime()

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    analysis = a1.analyze(
        visit_request
    )

    if not analysis.success:

        return {
            "system": "B4_RASE_NO_EAS",
            "decision": "FAIL",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Normal execution.
    # ---------------------------------------------------------

    if scenario == "S0_NORMAL":

        assignment = a2.assign(
            analysis.output
        )

        verification = a3.verify(
            assignment.output
        )

        return {
            "system": "B4_RASE_NO_EAS",
            "decision": "NO_ADAPTATION",
            "execution_success": assignment.success,
            "verification_success": verification.success,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Record A2 failure.
    # ---------------------------------------------------------

    runtime.record_agent_failure(
        "A2",
        "VetAssignment",
    )

    # ---------------------------------------------------------
    # Typed impact analysis.
    # ---------------------------------------------------------

    impact = runtime.analyze_impact(
        "A2"
    )

    impact_set = sorted(
        impact.keys()
    )

    # ---------------------------------------------------------
    # S4:
    # A4 is excluded because 'observes' is non-propagating.
    # ---------------------------------------------------------

    if scenario == "S4_IRRELEVANT_BRANCH":

        return {
            "system": "B4_RASE_NO_EAS",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": impact_set,
        }

    # ---------------------------------------------------------
    # No replacement.
    # ---------------------------------------------------------

    if a2_prime is None:

        return {
            "system": "B4_RASE_NO_EAS",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": impact_set,
        }

    # ---------------------------------------------------------
    # S5:
    # Contradictory evidence is intentionally introduced.
    #
    # B4 ignores EAS when making its decision.
    # ---------------------------------------------------------

    if scenario == "S5_UNCERTAIN_REPLACEMENT_EVIDENCE":

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "FAILURE",
            1.0,
        )

    # ---------------------------------------------------------
    # Reconfigure.
    # ---------------------------------------------------------

    transitions = runtime.reconfigure_dependency(
        "A2",
        "A2_prime",
    )

    replacement = a2_prime.assign(
        analysis.output
    )

    verification = a3.verify(
        replacement.output
    )

    # ---------------------------------------------------------
    # Commit.
    # ---------------------------------------------------------

    if replacement.success and verification.success:

        result = {
            "system": "B4_RASE_NO_EAS",
            "decision": "COMMIT",
            "execution_success": True,
            "verification_success": True,
            "reconfiguration_count": len(transitions),
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": impact_set,
        }

        if scenario == "S5_UNCERTAIN_REPLACEMENT_EVIDENCE":

            result["replacement_assurance"] = runtime.get_assurance(
                "A2_prime",
                "VetAssignment",
            )

        return result

    # ---------------------------------------------------------
    # Rollback.
    # ---------------------------------------------------------

    runtime.rollback_reconfiguration(
        transitions,
        "A2_prime",
    )

    result = {
        "system": "B4_RASE_NO_EAS",
        "decision": "ROLLBACK",
        "execution_success": False,
        "verification_success": False,
        "reconfiguration_count": len(transitions),
        "rollback": True,
        "final_architecture": architecture_string(runtime),
        "impact_set": impact_set,
    }

    if scenario == "S5_UNCERTAIN_REPLACEMENT_EVIDENCE":

        result["replacement_assurance"] = runtime.get_assurance(
            "A2_prime",
            "VetAssignment",
        )

    return result


# =====================================================================
# B5 - FULL RASE
# =====================================================================

def run_rase(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B5: Full RASE.

    Uses:
        - ERAM
        - EAS
        - TSDM
        - typed impact analysis
        - architectural reconfiguration
        - independent verification
        - rollback

    EAS is retained as part of the runtime state and is updated
    from observed execution and verification evidence.
    """

    runtime = create_rase_runtime()

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    analysis = a1.analyze(
        visit_request
    )

    if not analysis.success:

        return {
            "system": "B5_RASE",
            "decision": "FAIL",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Normal execution.
    # ---------------------------------------------------------

    if scenario == "S0_NORMAL":

        assignment = a2.assign(
            analysis.output
        )

        verification = a3.verify(
            assignment.output
        )

        return {
            "system": "B5_RASE",
            "decision": "NO_ADAPTATION",
            "execution_success": assignment.success,
            "verification_success": verification.success,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": [],
        }

    # ---------------------------------------------------------
    # Record A2 failure.
    # ---------------------------------------------------------

    runtime.record_agent_failure(
        "A2",
        "VetAssignment",
    )

    # ---------------------------------------------------------
    # Typed impact analysis.
    # ---------------------------------------------------------

    impact = runtime.analyze_impact(
        "A2"
    )

    impact_set = sorted(
        impact.keys()
    )

    # ---------------------------------------------------------
    # S4:
    # Typed model excludes A4.
    # ---------------------------------------------------------

    if scenario == "S4_IRRELEVANT_BRANCH":

        return {
            "system": "B5_RASE",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": impact_set,
        }

    # ---------------------------------------------------------
    # Determine replacement.
    # ---------------------------------------------------------

    if scenario == "S3_NO_REPLACEMENT":

        replacement = None

    else:

        replacement = runtime.find_alternative_agent(
            capability="VetAssignment",
            responsibility="AssignVet",
            excluded_agent="A2",
        )

    if replacement is None:

        return {
            "system": "B5_RASE",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": architecture_string(runtime),
            "impact_set": impact_set,
        }

    # ---------------------------------------------------------
    # S5:
    # Evidence-gated replacement decision.
    # ---------------------------------------------------------

    if scenario == "S5_UNCERTAIN_REPLACEMENT_EVIDENCE":

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "FAILURE",
            1.0,
        )

        replacement_assurance = runtime.get_assurance(
            "A2_prime",
            "VetAssignment",
        )

        assurance_threshold = 0.75

        if replacement_assurance < assurance_threshold:

            return {
                "system": "B5_RASE",
                "decision": "DEFER_UNCERTAIN",
                "execution_success": False,
                "verification_success": False,
                "reconfiguration_count": 0,
                "rollback": False,
                "final_architecture": architecture_string(runtime),
                "impact_set": impact_set,
                "replacement_assurance": replacement_assurance,
                "assurance_threshold": assurance_threshold,
            }

    # ---------------------------------------------------------
    # Architectural reconfiguration.
    # ---------------------------------------------------------

    transitions = runtime.reconfigure_dependency(
        "A2",
        replacement,
    )

    # ---------------------------------------------------------
    # Controlled replacement failure.
    # ---------------------------------------------------------

    if scenario == "S2_REPLACEMENT_FAIL":

        a2_prime.degraded = True

    else:

        a2_prime.degraded = False

    # ---------------------------------------------------------
    # Execute replacement.
    # ---------------------------------------------------------

    replacement_result = a2_prime.assign(
        analysis.output
    )

    # ---------------------------------------------------------
    # Independent verification.
    # ---------------------------------------------------------

    verification = a3.verify(
        replacement_result.output
    )

    # ---------------------------------------------------------
    # Commit or rollback.
    # ---------------------------------------------------------

    if replacement_result.success and verification.success:

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        decision = "COMMIT"
        rollback = False
        final_architecture = architecture_string(runtime)

    else:

        runtime.record_verification_failure(
            "A2_prime",
            "VetAssignment",
        )

        runtime.rollback_reconfiguration(
            transitions,
            replacement,
        )

        decision = "ROLLBACK"
        rollback = True
        final_architecture = architecture_string(runtime)

    return {
        "system": "B5_RASE",
        "decision": decision,
        "execution_success": replacement_result.success,
        "verification_success": verification.success,
        "reconfiguration_count": len(transitions),
        "rollback": rollback,
        "final_architecture": final_architecture,
        "impact_set": impact_set,
    }


# =====================================================================
# B6 - MAPE-K
# =====================================================================

def run_mapek(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    B6: Simplified MAPE-K-style baseline.

    Monitor:
        Detect agent failure.

    Analyze:
        Determine whether the failed assignment agent can be replaced.

    Plan:
        Select an available replacement.

    Execute:
        Reconfigure and execute the replacement.

    Knowledge:
        Store the resulting adaptation outcome.

    This baseline does not use:

        - typed semantic dependency propagation,
        - EAS assurance gating,
        - evidence-based uncertainty decisions,
        - RASE architectural impact analysis.
    """

    visit_request = {
        "pet_id": 1,
        "date": "2026-10-05",
    }

    # =========================================================
    # MONITOR / ANALYZE
    # =========================================================

    analysis = a1.analyze(
        visit_request
    )

    if not analysis.success:

        return {
            "system": "B6_MAPEK",
            "decision": "FAIL",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # =========================================================
    # NORMAL OPERATION
    # =========================================================

    if scenario == "S0_NORMAL":

        assignment = a2.assign(
            analysis.output
        )

        verification = a3.verify(
            assignment.output
        )

        return {
            "system": "B6_MAPEK",
            "decision": "NO_ADAPTATION",
            "execution_success": assignment.success,
            "verification_success": verification.success,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": [],
        }

    # =========================================================
    # NO REPLACEMENT
    # =========================================================

    if scenario == "S3_NO_REPLACEMENT":

        return {
            "system": "B6_MAPEK",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # =========================================================
    # IRRELEVANT BRANCH
    #
    # MAPE-K does not explicitly represent typed semantic
    # dependencies, so the observational branch is conservatively
    # treated as potentially affected.
    # =========================================================

    if scenario == "S4_IRRELEVANT_BRANCH":

        return {
            "system": "B6_MAPEK",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3|A4->A2",
            "impact_set": ["A2", "A3", "A4"],
        }

    # =========================================================
    # UNCERTAIN REPLACEMENT EVIDENCE
    #
    # Conventional MAPE-K has no explicit EAS assurance gate.
    # Therefore, it proceeds with the replacement and relies on
    # execution and verification.
    # =========================================================

    if scenario == "S5_UNCERTAIN_REPLACEMENT_EVIDENCE":

        if a2_prime is None:

            return {
                "system": "B6_MAPEK",
                "decision": "NO_REPLACEMENT",
                "execution_success": False,
                "verification_success": False,
                "reconfiguration_count": 0,
                "rollback": False,
                "final_architecture": "A1->A2->A3",
                "impact_set": ["A2", "A3"],
            }

        replacement = a2_prime.assign(
            analysis.output
        )

        if not replacement.success:

            return {
                "system": "B6_MAPEK",
                "decision": "ROLLBACK",
                "execution_success": False,
                "verification_success": False,
                "reconfiguration_count": 2,
                "rollback": True,
                "final_architecture": "A1->A2->A3",
                "impact_set": ["A2", "A3"],
            }

        verification = a3.verify(
            replacement.output
        )

        if verification.success:

            return {
                "system": "B6_MAPEK",
                "decision": "COMMIT",
                "execution_success": True,
                "verification_success": True,
                "reconfiguration_count": 2,
                "rollback": False,
                "final_architecture": "A1->A2_prime->A3",
                "impact_set": ["A2", "A3"],
            }

        return {
            "system": "B6_MAPEK",
            "decision": "ROLLBACK",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 2,
            "rollback": True,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # =========================================================
    # REPLACEMENT UNAVAILABLE
    # =========================================================

    if a2_prime is None:

        return {
            "system": "B6_MAPEK",
            "decision": "NO_REPLACEMENT",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 0,
            "rollback": False,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # =========================================================
    # PLAN / EXECUTE
    # =========================================================

    replacement = a2_prime.assign(
        analysis.output
    )

    # ---------------------------------------------------------
    # Failed replacement.
    # ---------------------------------------------------------

    if not replacement.success:

        return {
            "system": "B6_MAPEK",
            "decision": "ROLLBACK",
            "execution_success": False,
            "verification_success": False,
            "reconfiguration_count": 2,
            "rollback": True,
            "final_architecture": "A1->A2->A3",
            "impact_set": ["A2", "A3"],
        }

    # ---------------------------------------------------------
    # Independent verification.
    # ---------------------------------------------------------

    verification = a3.verify(
        replacement.output
    )

    # =========================================================
    # SUCCESSFUL ADAPTATION
    # =========================================================

    if replacement.success and verification.success:

        return {
            "system": "B6_MAPEK",
            "decision": "COMMIT",
            "execution_success": True,
            "verification_success": True,
            "reconfiguration_count": 2,
            "rollback": False,
            "final_architecture": "A1->A2_prime->A3",
            "impact_set": ["A2", "A3"],
        }

    # =========================================================
    # FAILED VERIFICATION -> ROLLBACK
    # =========================================================

    return {
        "system": "B6_MAPEK",
        "decision": "ROLLBACK",
        "execution_success": False,
        "verification_success": False,
        "reconfiguration_count": 2,
        "rollback": True,
        "final_architecture": "A1->A2->A3",
        "impact_set": ["A2", "A3"],
    }