from rase_runtime import RASERuntime


def print_separator(title):
    print("\n" + "=" * 46)
    print(title)
    print("=" * 46)


runtime = RASERuntime()

# ---------------------------------------------------------
# Register agents
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# Initial architecture
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# Initial evidence
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# STATE 0
# ---------------------------------------------------------

print_separator("STATE 0: NORMAL ARCHITECTURE")

runtime.print_state()

# ---------------------------------------------------------
# STATE 1: A2 failure
# ---------------------------------------------------------

runtime.record_agent_failure(
    "A2",
    "VetAssignment"
)

print_separator("STATE 1: A2 FAILURE")

runtime.print_state()

# ---------------------------------------------------------
# STATE 2: Impact analysis
# ---------------------------------------------------------

print_separator("STATE 2: IMPACT ANALYSIS")

impact = runtime.analyze_impact("A2")

for agent, score in impact.items():
    print(f"{agent}: impact={score:.2f}")

# ---------------------------------------------------------
# STATE 3: Alternative discovery
# ---------------------------------------------------------

state = runtime.eram.get_state()

failed_agent = "A2"

failed_capability = state["agents"][failed_agent]["capability"]
failed_responsibility = state["agents"][failed_agent]["responsibility"]

replacement = runtime.find_alternative_agent(
    capability=failed_capability,
    responsibility=failed_responsibility,
    excluded_agent=failed_agent
)

print_separator("STATE 3: ALTERNATIVE DISCOVERY")

print(f"Required capability: {failed_capability}")
print(f"Required responsibility: {failed_responsibility}")
print(f"Replacement candidate: {replacement}")

# ---------------------------------------------------------
# STATE 4: Reconfiguration
# ---------------------------------------------------------

if replacement:

    print_separator("STATE 4: RECONFIGURATION")

    transitions = runtime.reconfigure_dependency(
        failed_agent,
        replacement
    )

    print(f"Architectural transitions: {len(transitions)}")

    for transition in transitions:
        old = transition["old"]
        new = transition["new"]

        print(
            f"  {old['source']} "
            f"--[{old['relation_type']}]--> "
            f"{old['target']}"
            f"   =>   "
            f"{new['source']} "
            f"--[{new['relation_type']}]--> "
            f"{new['target']}"
        )

    print(f"Replacement selected: {replacement}")

    runtime.print_state()

else:

    print("No suitable replacement was found.")