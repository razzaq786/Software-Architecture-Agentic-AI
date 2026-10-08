from eas import EAS


def main():

    eas = EAS()

    # Successful assignment
    eas.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0
    )

    # Failed assignment
    eas.add_evidence(
        "A2",
        "VetAssignment",
        "FAILURE",
        1.0
    )

    eas.print_assurance(
        "A2",
        "VetAssignment"
    )


if __name__ == "__main__":
    main()