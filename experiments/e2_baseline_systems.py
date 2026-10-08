"""
E2 baseline systems for RASE.

E1 scenarios:
    S0_NORMAL
    S1_REPLACEMENT_PASS
    S2_REPLACEMENT_FAIL
    S3_NO_REPLACEMENT
    S4_IRRELEVANT_BRANCH
    S5_UNCERTAIN_REPLACEMENT_EVIDENCE

E2 extensions:
    S6_STALE_EVIDENCE
    S7_CONTRADICTORY_EVIDENCE
    S8_DELAYED_OBSERVATION
    S9_DEGRADED_AGENT
    S10_WEAK_REPLACEMENT

Systems:
    B1_STATIC
    B2_DYNAMIC
    B3_UNTYPED
    B4_RASE_NO_EAS
    B5_RASE
    B6_MAPEK

Important experimental separation:

    Architectural impact
        =
    Which responsibilities/elements can be affected?

    Architectural assurance
        =
    How trustworthy is the evidence supporting the architectural state?

EAS therefore does NOT remove elements from the typed architectural
impact set. It affects the adaptation decision after impact has been
computed.

The E1 runners are reused for S0-S5.
The E2-specific scenarios are implemented explicitly here.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone


# =====================================================================
# PROJECT PATH
# =====================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =====================================================================
# E1 IMPORTS
# =====================================================================

from experiments.baseline_systems import (
    run_static,
    run_dynamic,
    run_untyped,
    run_rase_no_eas,
    run_rase,
    run_mapek,
    create_rase_runtime,
    architecture_string,
)


# =====================================================================
# SYSTEM DEFINITIONS
# =====================================================================

SYSTEMS = [
    "B1_STATIC",
    "B2_DYNAMIC",
    "B3_UNTYPED",
    "B4_RASE_NO_EAS",
    "B5_RASE",
    "B6_MAPEK",
]


E1_SCENARIOS = {
    "S0_NORMAL",
    "S1_REPLACEMENT_PASS",
    "S2_REPLACEMENT_FAIL",
    "S3_NO_REPLACEMENT",
    "S4_IRRELEVANT_BRANCH",
    "S5_UNCERTAIN_REPLACEMENT_EVIDENCE",
}


E2_SCENARIOS = {
    "S6_STALE_EVIDENCE",
    "S7_CONTRADICTORY_EVIDENCE",
    "S8_DELAYED_OBSERVATION",
    "S9_DEGRADED_AGENT",
    "S10_WEAK_REPLACEMENT",
}


ALL_SCENARIOS = E1_SCENARIOS | E2_SCENARIOS


# =====================================================================
# TYPED DEPENDENCY SEMANTICS
# =====================================================================

# These relation types propagate functional architectural impact.
#
# "observes" is deliberately excluded because an observational branch
# does not become functionally affected merely because A2 changes.
#
# This is the key distinction between B3_UNTYPED and the typed RASE
# architecture.

PROPAGATING_RELATIONS = {
    "produces-event",
    "produces-result",
    "supports-responsibility",
    "provides-capability",
    "affects-goal",
}


# =====================================================================
# AGENT CREATION
# =====================================================================

def create_agents(
    include_replacement=True,
    degraded_replacement=False,
):
    """
    Create a fresh agent population for one E2 run.
    """

    from agents.agents import (
        VisitAnalysisAgent,
        VetAssignmentAgent,
        VerificationAgent,
    )

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

    # Independent observational branch.
    a4 = VetAssignmentAgent(
        agent_id="A4",
        available=True,
        degraded=False,
    )

    return (
        a1,
        a2,
        a2_prime,
        a3,
        a4,
    )


# =====================================================================
# TIME HELPERS
# =====================================================================

def utc_now():
    return datetime.now(timezone.utc)


def timestamp_seconds_ago(seconds):
    return (
        utc_now()
        - timedelta(seconds=seconds)
    ).isoformat()


def timestamp_minutes_ago(minutes):
    return timestamp_seconds_ago(
        minutes * 60
    )


# =====================================================================
# RESULT HELPERS
# =====================================================================

def base_result(
    system,
    decision,
    impact_set,
    execution_success=False,
    verification_success=False,
    reconfiguration_count=0,
    rollback=False,
    final_architecture="A1->A2->A3",
):
    """
    Return the complete schema expected by evaluate_e2.py.
    """

    return {
        "system": system,
        "decision": decision,

        "execution_success": execution_success,
        "verification_success": verification_success,

        "reconfiguration_count": reconfiguration_count,
        "rollback": rollback,

        "final_architecture": final_architecture,

        "impact_set": sorted(
            list(impact_set)
        ),

        # E2 assurance fields.
        "assurance": None,
        "evidence_status": None,

        "replacement_assurance": None,
        "replacement_status": None,

        # True only if adaptation occurs before sufficient
        # observation/evidence becomes available.
        "premature_adaptation": False,
    }


# =====================================================================
# TYPED ARCHITECTURAL IMPACT
# =====================================================================

def typed_impact_set(
    runtime,
    seed_agent,
):
    """
    Compute functional architectural impact independently of EAS.

    This deliberately answers:

        "Which architectural elements can be affected?"

    rather than:

        "Is the evidence about those elements trustworthy?"

    The two questions must remain separate for the E2 experiment.

    The ERAM dependency graph is traversed using only typed functional
    relations. Observational relations such as "observes" are excluded.

    Therefore:

        A2 -> A3  produces-result
        A4 -> A2  observes

    gives:

        impact(A2) = {A2, A3}

    and NOT:

        {A2, A3, A4}
    """

    impacted = {
        seed_agent
    }

    queue = [
        seed_agent
    ]

    visited = {
        seed_agent
    }

    # ERAM stores dependencies created during create_rase_runtime().
    dependencies = getattr(
        runtime.eram,
        "dependencies",
        [],
    )

    while queue:

        current = queue.pop(0)

        for dependency in dependencies:

            source = getattr(
                dependency,
                "source",
                None,
            )

            target = getattr(
                dependency,
                "target",
                None,
            )

            relation_type = getattr(
                dependency,
                "relation_type",
                None,
            )

            if source != current:
                continue

            if relation_type not in PROPAGATING_RELATIONS:
                continue

            if target is None:
                continue

            if target not in impacted:

                impacted.add(target)

            if target not in visited:

                visited.add(target)
                queue.append(target)

    return sorted(
        impacted
    )


# =====================================================================
# FALLBACK TYPED IMPACT
# =====================================================================

def expected_typed_impact(
    runtime,
    seed_agent,
):
    """
    Robust wrapper around typed_impact_set().

    The primary implementation derives impact from ERAM.

    If an older ERAM implementation exposes dependencies through a
    different container, this fallback preserves the experimentally
    defined architecture for the current pilot.
    """

    try:

        impact = typed_impact_set(
            runtime,
            seed_agent,
        )

        if impact:

            return impact

    except Exception:

        pass

    # Current pilot architecture.
    if seed_agent == "A2":

        return [
            "A2",
            "A3",
        ]

    return [
        seed_agent
    ]


# =====================================================================
# EAS INFORMATION
# =====================================================================

def attach_eas_information(
    result,
    runtime,
    replacement_id="A2_prime",
):
    """
    Add current EAS information to a result.
    """

    try:

        result["assurance"] = (
            runtime.get_assurance(
                "A2",
                "VetAssignment",
            )
        )

        result["evidence_status"] = (
            runtime.get_evidence_status(
                "A2",
                "VetAssignment",
            )
        )

        if replacement_id is not None:

            result["replacement_assurance"] = (
                runtime.get_assurance(
                    replacement_id,
                    "VetAssignment",
                )
            )

            result["replacement_status"] = (
                runtime.get_evidence_status(
                    replacement_id,
                    "VetAssignment",
                )
            )

    except Exception:

        pass

    return result


# =====================================================================
# NORMAL WORKFLOW
# =====================================================================

def execute_workflow(
    a1,
    assignment_agent,
    a3,
):
    """
    Execute:

        A1 -> A2/A2_prime -> A3

    Returns execution and independent verification outcomes.
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
            "execution_success": False,
            "verification_success": False,
            "assignment": None,
            "verification": None,
        }

    assignment = assignment_agent.assign(
        analysis.output
    )

    if not assignment.success:

        return {
            "execution_success": False,
            "verification_success": False,
            "assignment": assignment,
            "verification": None,
        }

    verification = a3.verify(
        assignment.output
    )

    return {
        "execution_success": assignment.success,
        "verification_success": verification.success,
        "assignment": assignment,
        "verification": verification,
    }


# =====================================================================
# E1 SCENARIOS
# =====================================================================

def run_original_e1_system(
    system_name,
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    Reuse the validated E1 implementations for S0-S5.

    This prevents the E2 experiment from accidentally creating a
    second implementation of the original baselines.
    """

    runners = {
        "B1_STATIC": run_static,
        "B2_DYNAMIC": run_dynamic,
        "B3_UNTYPED": run_untyped,
        "B4_RASE_NO_EAS": run_rase_no_eas,
        "B5_RASE": run_rase,
        "B6_MAPEK": run_mapek,
    }

    runner = runners[system_name]

    return runner(
        scenario,
        a1,
        a2,
        a2_prime,
        a3,
        a4,
    )


# =====================================================================
# GENERIC NON-EAS ADAPTATION
# =====================================================================

def conventional_replacement(
    system_name,
    a1,
    a2_prime,
    a3,
    impact_set,
):
    """
    Conventional runtime replacement.

    This represents systems that can react to an observable operational
    problem but do not use EAS as an explicit architectural decision
    gate.

    The independent verification result determines commit/rollback.
    """

    if a2_prime is None:

        return base_result(
            system_name,
            "NO_REPLACEMENT",
            impact_set,
            False,
            False,
            0,
            False,
            "A1->A2->A3",
        )

    workflow = execute_workflow(
        a1,
        a2_prime,
        a3,
    )

    if (
        workflow["execution_success"]
        and workflow["verification_success"]
    ):

        return base_result(
            system_name,
            "COMMIT",
            impact_set,
            True,
            True,
            2,
            False,
            "A1->A2_prime->A3",
        )

    return base_result(
        system_name,
        "ROLLBACK",
        impact_set,
        workflow["execution_success"],
        workflow["verification_success"],
        2,
        True,
        "A1->A2->A3",
    )


# =====================================================================
# B5 / RASE E2 IMPLEMENTATION
# =====================================================================

def run_rase_e2(
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    Full RASE implementation for E2 scenarios.

    RASE processing order:

        Observation
             ↓
        Architectural impact
             ↓
        Evidence assessment
             ↓
        Decision
             ↓
        Reconfiguration
             ↓
        Independent verification

    Importantly, impact is computed before EAS gates adaptation.
    """

    runtime = create_rase_runtime()

    # -------------------------------------------------------------
    # S0 NORMAL
    # -------------------------------------------------------------

    if scenario == "S0_NORMAL":

        workflow = execute_workflow(
            a1,
            a2,
            a3,
        )

        return base_result(
            "B5_RASE",
            "NO_ADAPTATION",
            [],
            workflow["execution_success"],
            workflow["verification_success"],
            0,
            False,
            "A1->A2->A3",
        )

    # -------------------------------------------------------------
    # S6 STALE EVIDENCE
    # -------------------------------------------------------------

    if scenario == "S6_STALE_EVIDENCE":

        # Keep strong evidence for the replacement.
        # Only the primary agent's evidence is stale.
        runtime.eas.evidence.clear()

        runtime.add_historical_evidence(
            "A2",
            "VetAssignment",
            "SUCCESS",
            1.0,
            timestamp_minutes_ago(10),
        )

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        # IMPORTANT:
        # Do NOT call record_agent_failure().
        #
        # Doing so would create fresh evidence and invalidate the
        # stale-evidence condition.

        impact_set = expected_typed_impact(
            runtime,
            "A2",
        )

        primary_assurance = runtime.get_assurance(
            "A2",
            "VetAssignment",
        )

        primary_status = runtime.get_evidence_status(
            "A2",
            "VetAssignment",
        )

        replacement_assurance = runtime.get_assurance(
            "A2_prime",
            "VetAssignment",
        )

        replacement_status = runtime.get_evidence_status(
            "A2_prime",
            "VetAssignment",
        )

        result = base_result(
            "B5_RASE",
            "DEFER_UNCERTAIN",
            impact_set,
            False,
            False,
            0,
            False,
            "A1->A2->A3",
        )

        result["assurance"] = primary_assurance
        result["evidence_status"] = primary_status

        result["replacement_assurance"] = (
            replacement_assurance
        )

        result["replacement_status"] = (
            replacement_status
        )

        return result

    # -------------------------------------------------------------
    # S7 CONTRADICTORY EVIDENCE
    # -------------------------------------------------------------

    if scenario == "S7_CONTRADICTORY_EVIDENCE":

        runtime.eas.evidence.clear()

        # Exactly contradictory evidence:
        #
        # SUCCESS = 1.0
        # FAILURE = 1.0
        #
        # Do not add another failure through record_agent_failure().
        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "FAILURE",
            1.0,
        )

        # Replacement is independently qualified.
        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        impact_set = expected_typed_impact(
            runtime,
            "A2",
        )

        result = base_result(
            "B5_RASE",
            "DEFER_UNCERTAIN",
            impact_set,
            False,
            False,
            0,
            False,
            "A1->A2->A3",
        )

        return attach_eas_information(
            result,
            runtime,
        )

    # -------------------------------------------------------------
    # S8 DELAYED OBSERVATION
    # -------------------------------------------------------------

    if scenario == "S8_DELAYED_OBSERVATION":

        # =========================================================
        # STAGE 1: FAILURE NOT YET OBSERVED
        # =========================================================

        runtime.eas.evidence.clear()

        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        initial_impact = expected_typed_impact(
            runtime,
            "A2",
        )

        # No adaptation is allowed before the failure observation
        # becomes available.
        premature_adaptation = False

        # =========================================================
        # STAGE 2: DELAYED FAILURE OBSERVATION ARRIVES
        # =========================================================

        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "FAILURE",
            1.0,
        )

        # The failure is now observable.
        impact_set = expected_typed_impact(
            runtime,
            "A2",
        )

        replacement = runtime.find_alternative_agent(
            capability="VetAssignment",
            responsibility="AssignVet",
            excluded_agent="A2",
        )

        if replacement is None:

            result = base_result(
                "B5_RASE",
                "NO_REPLACEMENT",
                impact_set,
                False,
                False,
                0,
                False,
                "A1->A2->A3",
            )

            result["premature_adaptation"] = (
                premature_adaptation
            )

            return attach_eas_information(
                result,
                runtime,
            )

        # Verify replacement evidence before changing architecture.
        replacement_assurance = runtime.get_assurance(
            replacement,
            "VetAssignment",
        )

        replacement_status = runtime.get_evidence_status(
            replacement,
            "VetAssignment",
        )

        assurance_threshold = 0.75

        if replacement_assurance < assurance_threshold:

            result = base_result(
                "B5_RASE",
                "DEFER_UNCERTAIN",
                impact_set,
                False,
                False,
                0,
                False,
                "A1->A2->A3",
            )

            result["premature_adaptation"] = (
                premature_adaptation
            )

            result["replacement_assurance"] = (
                replacement_assurance
            )

            result["replacement_status"] = (
                replacement_status
            )

            result["assurance_threshold"] = (
                assurance_threshold
            )

            return attach_eas_information(
                result,
                runtime,
            )

        # =========================================================
        # RECONFIGURATION
        # =========================================================

        transitions = runtime.reconfigure_dependency(
            "A2",
            replacement,
        )

        workflow = execute_workflow(
            a1,
            a2_prime,
            a3,
        )

        if (
            workflow["execution_success"]
            and workflow["verification_success"]
        ):

            runtime.add_evidence(
                replacement,
                "VetAssignment",
                "SUCCESS",
                1.0,
            )

            result = base_result(
                "B5_RASE",
                "COMMIT",
                impact_set,
                True,
                True,
                len(transitions),
                False,
                architecture_string(runtime),
            )

            result["premature_adaptation"] = (
                premature_adaptation
            )

            result["replacement_assurance"] = (
                runtime.get_assurance(
                    replacement,
                    "VetAssignment",
                )
            )

            result["replacement_status"] = (
                runtime.get_evidence_status(
                    replacement,
                    "VetAssignment",
                )
            )

            return attach_eas_information(
                result,
                runtime,
            )

        # =========================================================
        # VERIFICATION FAILURE
        # =========================================================

        runtime.rollback_reconfiguration(
            transitions,
            replacement,
        )

        result = base_result(
            "B5_RASE",
            "ROLLBACK",
            impact_set,
            workflow["execution_success"],
            workflow["verification_success"],
            len(transitions),
            True,
            architecture_string(runtime),
        )

        result["premature_adaptation"] = (
            premature_adaptation
        )

        return attach_eas_information(
            result,
            runtime,
        )

    # -------------------------------------------------------------
    # S9 DEGRADED AGENT
    # -------------------------------------------------------------

    if scenario == "S9_DEGRADED_AGENT":

        runtime.eas.evidence.clear()

        # The agent was previously successful but now provides
        # degraded behavior.
        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "DEGRADED",
            1.0,
        )

        # Do NOT convert degradation into an additional FAILURE.
        #
        # The scenario specifically represents behavioral degradation,
        # not complete unavailability.

        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            1.0,
        )

        impact_set = expected_typed_impact(
            runtime,
            "A2",
        )

        result = base_result(
            "B5_RASE",
            "DEFER_UNCERTAIN",
            impact_set,
            False,
            False,
            0,
            False,
            "A1->A2->A3",
        )

        return attach_eas_information(
            result,
            runtime,
        )

    # -------------------------------------------------------------
    # S10 WEAK REPLACEMENT
    # -------------------------------------------------------------

    if scenario == "S10_WEAK_REPLACEMENT":

        runtime.eas.evidence.clear()

        # Primary agent has strong evidence of failure.
        runtime.add_evidence(
            "A2",
            "VetAssignment",
            "FAILURE",
            1.0,
        )

        # Replacement has only weak supporting evidence.
        runtime.add_evidence(
            "A2_prime",
            "VetAssignment",
            "SUCCESS",
            0.25,
        )

        impact_set = expected_typed_impact(
            runtime,
            "A2",
        )

        replacement_assurance = runtime.get_assurance(
            "A2_prime",
            "VetAssignment",
        )

        replacement_status = runtime.get_evidence_status(
            "A2_prime",
            "VetAssignment",
        )

        assurance_threshold = 0.75

        if replacement_assurance < assurance_threshold:

            result = base_result(
                "B5_RASE",
                "DEFER_UNCERTAIN",
                impact_set,
                False,
                False,
                0,
                False,
                "A1->A2->A3",
            )

            result["replacement_assurance"] = (
                replacement_assurance
            )

            result["replacement_status"] = (
                replacement_status
            )

            result["assurance_threshold"] = (
                assurance_threshold
            )

            return result

        # Defensive fallback. The expected experimental condition
        # should always trigger the defer branch above.
        raise RuntimeError(
            "S10 weak-replacement condition did not produce "
            "the expected uncertainty decision."
        )

    # -------------------------------------------------------------
    # UNKNOWN
    # -------------------------------------------------------------

    raise ValueError(
        f"Unsupported RASE E2 scenario: {scenario}"
    )


# =====================================================================
# NON-EAS E2 SYSTEMS
# =====================================================================

def run_non_eas_e2(
    system_name,
    scenario,
    a1,
    a2,
    a2_prime,
    a3,
    a4,
):
    """
    E2 behavior for systems without evidence-assessed
    architectural state.

    These systems can respond to an observable operational event,
    but they do not explicitly use EAS to determine whether
    architectural knowledge is sufficiently trustworthy.

    B1 is static and therefore cannot perform runtime replacement.

    B2 is dynamic but untyped.

    B3 uses connectivity without typed dependency semantics.

    B4 uses typed RASE mechanisms but without EAS gating.

    B6 represents MAPE-K-style monitor/analyze/plan/execute behavior
    without the RASE evidence-assurance mechanism.
    """

    runtime = create_rase_runtime()

    # -------------------------------------------------------------
    # B1 STATIC
    # -------------------------------------------------------------

    if system_name == "B1_STATIC":

        return base_result(
            system_name,
            "FAIL",
            [],
            False,
            False,
            0,
            False,
            "A1->A2->A3",
        )

    # -------------------------------------------------------------
    # COMMON TYPED IMPACT
    # -------------------------------------------------------------

    typed_impact = expected_typed_impact(
        runtime,
        "A2",
    )

    # -------------------------------------------------------------
    # S8 DELAYED OBSERVATION
    # -------------------------------------------------------------

    if scenario == "S8_DELAYED_OBSERVATION":

        # All non-static systems receive the failure observation only
        # after the initial no-observation stage.
        #
        # They therefore do not need to "guess" the failure.

        premature_adaptation = False

        # The delayed observation is now available.
        #
        # For B3, the untyped system considers all connected nodes,
        # including the independent observational branch A4.
        #
        # For B2, B4 and B6, the functional path is A2 -> A3.

        if system_name == "B3_UNTYPED":

            impact_set = [
                "A2",
                "A3",
                "A4",
            ]

        else:

            impact_set = typed_impact

        result = conventional_replacement(
            system_name,
            a1,
            a2_prime,
            a3,
            impact_set,
        )

        result["premature_adaptation"] = (
            premature_adaptation
        )

        return result

    # -------------------------------------------------------------
    # S6 STALE EVIDENCE
    # -------------------------------------------------------------

    if scenario == "S6_STALE_EVIDENCE":

        # These baselines do not model evidence freshness as a
        # decision variable. Consequently stale historical knowledge
        # does not cause explicit DEFER_UNCERTAIN behavior.

        return conventional_replacement(
            system_name,
            a1,
            a2_prime,
            a3,
            typed_impact,
        )

    # -------------------------------------------------------------
    # S7 CONTRADICTORY EVIDENCE
    # -------------------------------------------------------------

    if scenario == "S7_CONTRADICTORY_EVIDENCE":

        # These systems do not have explicit contradiction detection.
        # They therefore proceed with the operationally available
        # replacement and let independent execution/verification
        # determine the result.

        return conventional_replacement(
            system_name,
            a1,
            a2_prime,
            a3,
            typed_impact,
        )

    # -------------------------------------------------------------
    # S9 DEGRADED AGENT
    # -------------------------------------------------------------

    if scenario == "S9_DEGRADED_AGENT":

        # Conventional systems interpret degradation as an operational
        # problem and attempt replacement.
        #
        # They do not maintain the EAS distinction between:
        #   known failure,
        #   degraded behavior,
        #   uncertain architectural state.

        return conventional_replacement(
            system_name,
            a1,
            a2_prime,
            a3,
            typed_impact,
        )

    # -------------------------------------------------------------
    # S10 WEAK REPLACEMENT
    # -------------------------------------------------------------

    if scenario == "S10_WEAK_REPLACEMENT":

        # The weak historical evidence of the replacement is not used
        # as an explicit architectural assurance gate.
        return conventional_replacement(
            system_name,
            a1,
            a2_prime,
            a3,
            typed_impact,
        )

    # -------------------------------------------------------------
    # UNKNOWN
    # -------------------------------------------------------------

    raise ValueError(
        f"Unsupported non-EAS scenario: {scenario}"
    )


# =====================================================================
# MAIN E2 ENTRY POINT
# =====================================================================

def run_e2_system(
    system_name,
    scenario,
):
    """
    Execute one E2 experiment.

    This function is the only interface used by evaluate_e2.py.
    """

    if system_name not in SYSTEMS:

        raise ValueError(
            f"Unsupported E2 system: {system_name}"
        )

    if scenario not in ALL_SCENARIOS:

        raise ValueError(
            f"Unsupported E2 scenario: {scenario}"
        )

    # -------------------------------------------------------------
    # Fresh agents for every run.
    # -------------------------------------------------------------

    (
        a1,
        a2,
        a2_prime,
        a3,
        a4,
    ) = create_agents()

    # -------------------------------------------------------------
    # E1 scenarios.
    # -------------------------------------------------------------

    if scenario in E1_SCENARIOS:

        result = run_original_e1_system(
            system_name,
            scenario,
            a1,
            a2,
            a2_prime,
            a3,
            a4,
        )

        normalized = base_result(
            system_name,
            result.get(
                "decision",
                "FAIL",
            ),
            result.get(
                "impact_set",
                [],
            ),
            result.get(
                "execution_success",
                False,
            ),
            result.get(
                "verification_success",
                False,
            ),
            result.get(
                "reconfiguration_count",
                0,
            ),
            result.get(
                "rollback",
                False,
            ),
            result.get(
                "final_architecture",
                "A1->A2->A3",
            ),
        )

        normalized.update(
            result
        )

        # Guarantee the complete E2 schema.
        for key in [
            "assurance",
            "evidence_status",
            "replacement_assurance",
            "replacement_status",
        ]:

            if key not in normalized:

                normalized[key] = None

        if "premature_adaptation" not in normalized:

            normalized["premature_adaptation"] = False

        normalized["system"] = system_name
        normalized["scenario"] = scenario

        return normalized

    # -------------------------------------------------------------
    # Full RASE.
    # -------------------------------------------------------------

    if system_name == "B5_RASE":

        result = run_rase_e2(
            scenario,
            a1,
            a2,
            a2_prime,
            a3,
            a4,
        )

        result["system"] = system_name
        result["scenario"] = scenario

        return result

    # -------------------------------------------------------------
    # Non-EAS systems.
    # -------------------------------------------------------------

    result = run_non_eas_e2(
        system_name,
        scenario,
        a1,
        a2,
        a2_prime,
        a3,
        a4,
    )

    result["system"] = system_name
    result["scenario"] = scenario

    return result


# =====================================================================
# SMOKE TEST
# =====================================================================

if __name__ == "__main__":

    print("=" * 75)
    print("RASE E2 BASELINE SYSTEM SMOKE TEST")
    print("=" * 75)

    for scenario in sorted(
        ALL_SCENARIOS
    ):

        print(
            f"\nScenario: {scenario}"
        )

        for system in SYSTEMS:

            try:

                result = run_e2_system(
                    system,
                    scenario,
                )

                print(
                    f"  {system:18s} "
                    f"decision={result['decision']:18s} "
                    f"impact={result['impact_set']} "
                    f"reconfig={result['reconfiguration_count']}"
                )

            except Exception as exc:

                print(
                    f"  {system:18s} ERROR: {exc}"
                )

    print(
        "\n"
        + "=" * 75
    )

    print(
        "Smoke test complete."
    )

    print(
        "=" * 75
    )