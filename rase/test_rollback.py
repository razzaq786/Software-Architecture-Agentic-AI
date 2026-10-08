import sys
import os

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from agents.agents import (
    VisitAnalysisAgent,
    VetAssignmentAgent,
    VerificationAgent
)

from rase_runtime import RASERuntime


def separator(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# =========================================================
# Create agents
# =========================================================

a1 = VisitAnalysisAgent()

a2 = VetAssignmentAgent(
    agent_id="A2"
)

# Deliberately create a degraded replacement.
a2_prime = VetAssignmentAgent(
    agent_id="A2_prime",
    degraded=True
)

a3 = VerificationAgent()


# =========================================================
# Create RASE runtime
# =========================================================

runtime = RASERuntime()


# =========================================================
# Register agents
# =========================================================

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


# =========================================================
# Initial architecture
# =========================================================

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


# =========================================================
# Initial evidence
# =========================================================

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


# =========================================================
# STEP 1 — Generate visit event
# =========================================================

separator("STEP 1: VISIT ANALYSIS")

visit_request = {
    "pet_id": 1,
    "date": "2026-10-05"
}

analysis_result = a1.analyze(
    visit_request
)

print(
    "A1 success:",
    analysis_result.success
)

print(
    "Event:",
    analysis_result.output
)


# =========================================================
# STEP 2 — A2 failure
# =========================================================

separator("STEP 2: A2 FAILURE")

a2.available = False

runtime.record_agent_failure(
    "A2",
    "VetAssignment"
)

print(
    "A2 status:",
    runtime.eram.get_state()["agents"]["A2"]["status"]
)

print(
    "A2 assurance:",
    runtime.get_assurance(
        "A2",
        "VetAssignment"
    )
)


# =========================================================
# STEP 3 — Impact analysis
# =========================================================

separator("STEP 3: IMPACT ANALYSIS")

impact = runtime.analyze_impact(
    "A2"
)

for agent, score in impact.items():

    print(
        f"{agent}: impact={score:.2f}"
    )


# =========================================================
# STEP 4 — Alternative discovery
# =========================================================

separator("STEP 4: ALTERNATIVE DISCOVERY")

replacement = runtime.find_alternative_agent(
    capability="VetAssignment",
    responsibility="AssignVet",
    excluded_agent="A2"
)

print(
    "Replacement:",
    replacement
)


# =========================================================
# STEP 5 — Reconfiguration
# =========================================================

separator("STEP 5: RECONFIGURATION")

transitions = runtime.reconfigure_dependency(
    "A2",
    replacement
)

print(
    "Transitions:",
    len(transitions)
)

for transition in transitions:

    old = transition["old"]
    new = transition["new"]

    print(
        f"{old['source']} "
        f"--[{old['relation_type']}]--> "
        f"{old['target']}"
        f"  =>  "
        f"{new['source']} "
        f"--[{new['relation_type']}]--> "
        f"{new['target']}"
    )


# =========================================================
# STEP 6 — Execute degraded replacement
# =========================================================

separator("STEP 6: EXECUTE DEGRADED REPLACEMENT")

replacement_result = a2_prime.assign(
    analysis_result.output
)

print(
    "A2_prime success:",
    replacement_result.success
)

print(
    "A2_prime output:",
    replacement_result.output
)


# =========================================================
# STEP 7 — Independent verification
# =========================================================

separator("STEP 7: INDEPENDENT VERIFICATION")

verification_result = a3.verify(
    replacement_result.output
)

print(
    "A3 verification:",
    verification_result.success
)

print(
    "Verification output:",
    verification_result.output
)


# =========================================================
# STEP 8 — Verification failure
# =========================================================

separator("STEP 8: VERIFICATION DECISION")

if not verification_result.success:

    print(
        "VERIFICATION FAILED"
    )

    print(
        "Replacement architecture is not accepted."
    )

    runtime.record_verification_failure(
        "A2_prime",
        "VetAssignment"
    )

    print(
        "A2_prime assurance after failure:",
        runtime.get_assurance(
            "A2_prime",
            "VetAssignment"
        )
    )


# =========================================================
# STEP 9 — Rollback
# =========================================================

separator("STEP 9: ARCHITECTURAL ROLLBACK")

rollback_records = runtime.rollback_reconfiguration(
    transitions,
    replacement
)

print(
    "Rollback transitions:",
    len(rollback_records)
)

for record in rollback_records:

    removed = record["removed"]
    restored = record["restored"]

    print(
        f"Removed: "
        f"{removed['source']} "
        f"--[{removed['relation_type']}]--> "
        f"{removed['target']}"
    )

    print(
        f"Restored: "
        f"{restored['source']} "
        f"--[{restored['relation_type']}]--> "
        f"{restored['target']}"
    )


# =========================================================
# STEP 10 — Final state
# =========================================================

separator("STEP 10: FINAL RASE STATE")

runtime.print_state()