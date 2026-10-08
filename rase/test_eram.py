from eram import ERAM


def main():

    eram = ERAM()

    # Register agents
    eram.register_agent(
        "A1",
        "VisitAnalysis",
        "AnalyzeVisit"
    )

    eram.register_agent(
        "A2",
        "VetAssignment",
        "AssignVet"
    )

    eram.register_agent(
        "A3",
        "AssignmentVerification",
        "VerifyAssignment"
    )

    # Add typed dependencies
    eram.add_dependency(
        "A1",
        "A2",
        "produces-event"
    )

    eram.add_dependency(
        "A2",
        "A3",
        "produces-result"
    )

    # Display architecture
    eram.print_state()


if __name__ == "__main__":
    main()