from tsdm import TSDM


tsdm = TSDM()

tsdm.add_dependency(
    "A1",
    "A2",
    "produces-event",
    propagation_weight=0.9
)

tsdm.add_dependency(
    "A2",
    "A3",
    "produces-result",
    propagation_weight=0.8
)

tsdm.print_dependencies()


print("\n=== TEST 1: HIGH ASSURANCE ===")

high_assurance = {
    "A1": 1.0,
    "A2": 1.0,
    "A3": 1.0,
}

impact = tsdm.propagate_impact(
    changed_agent="A2",
    assurance=high_assurance,
)

for agent, score in impact.items():
    print(
        f"{agent}: impact={score:.2f}"
    )


print("\n=== TEST 2: LOW A3 ASSURANCE ===")

low_assurance = {
    "A1": 1.0,
    "A2": 1.0,
    "A3": 0.5,
}

impact = tsdm.propagate_impact(
    changed_agent="A2",
    assurance=low_assurance,
)

for agent, score in impact.items():
    print(
        f"{agent}: impact={score:.2f}"
    )