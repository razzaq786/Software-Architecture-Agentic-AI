from rase_runtime import RASERuntime


# =================================================
# 1. Create RASE runtime
# =================================================

rase = RASERuntime()


# =================================================
# 2. Register agents
# =================================================

rase.register_agent(
    "A1",
    "VisitAnalysis",
    "AnalyzeVisit",
)

rase.register_agent(
    "A2",
    "VetAssignment",
    "AssignVet",
)

rase.register_agent(
    "A3",
    "AssignmentVerification",
    "VerifyAssignment",
)


# =================================================
# 3. Define architecture
# =================================================

rase.add_dependency(
    "A1",
    "A2",
    "produces-event",
    propagation_weight=0.9,
)

rase.add_dependency(
    "A2",
    "A3",
    "produces-result",
    propagation_weight=0.8,
)


# =================================================
# 4. Establish normal runtime evidence
# =================================================

rase.add_evidence(
    "A1",
    "VisitAnalysis",
    "SUCCESS",
    1.0,
)

rase.add_evidence(
    "A2",
    "VetAssignment",
    "SUCCESS",
    1.0,
)

rase.add_evidence(
    "A3",
    "AssignmentVerification",
    "SUCCESS",
    1.0,
)


print("\n==============================================")
print("STATE 0: NORMAL OPERATION")
print("==============================================")

rase.print_state()


# =================================================
# 5. A2 becomes unavailable
# =================================================

print("\n==============================================")
print("STATE 1: A2 FAILURE")
print("==============================================")

rase.record_agent_failure(
    agent_id="A2",
    capability="VetAssignment",
)


# =================================================
# 6. Display changed architecture
# =================================================

rase.print_state()


# =================================================
# 7. Impact analysis
# =================================================

print("\n==============================================")
print("STATE 2: IMPACT ANALYSIS")
print("==============================================")

impact = rase.analyze_impact(
    changed_agent="A2",
)

for agent, score in impact.items():

    print(
        f"{agent}: impact={score:.2f}"
    )