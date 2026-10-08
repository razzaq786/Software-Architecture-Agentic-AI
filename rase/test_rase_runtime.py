from rase_runtime import RASERuntime


rase = RASERuntime()


# -------------------------------------------------
# 1. Register agents
# -------------------------------------------------

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


# -------------------------------------------------
# 2. Define typed architectural dependencies
# -------------------------------------------------

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


# -------------------------------------------------
# 3. Add runtime evidence
# -------------------------------------------------

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
    "A2",
    "VetAssignment",
    "FAILURE",
    1.0,
)

rase.add_evidence(
    "A3",
    "AssignmentVerification",
    "SUCCESS",
    1.0,
)


# -------------------------------------------------
# 4. Display integrated architectural state
# -------------------------------------------------

rase.print_state()


# -------------------------------------------------
# 5. Analyze impact of A2 change
# -------------------------------------------------

print("\n=== IMPACT ANALYSIS: A2 CHANGE ===")

impact = rase.analyze_impact(
    changed_agent="A2"
)

for agent, score in impact.items():

    print(
        f"{agent}: impact={score:.2f}"
    )