from agents import (
    VisitAnalysisAgent,
    VetAssignmentAgent,
    VerificationAgent
)


def main():

    a1 = VisitAnalysisAgent()
    a2 = VetAssignmentAgent()
    a3 = VerificationAgent()

    visit = a1.analyze_visit(
        pet_id=1,
        date="2026-10-05"
    )

    print("\nA1 RESULT")
    print(visit)

    assignment = a2.assign_vet(
        visit.output
    )

    print("\nA2 RESULT")
    print(assignment)

    verification = a3.verify(
        assignment.output
    )

    print("\nA3 RESULT")
    print(verification)


if __name__ == "__main__":
    main()