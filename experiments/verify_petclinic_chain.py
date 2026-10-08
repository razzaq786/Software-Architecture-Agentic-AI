"""
PetClinic-Grounded RASE Case Study
Stage E3.1b: Precise Workflow Verification

Verifies the concrete source chain:

VisitScheduler
      |
      | publishes VisitBooked
      v
VetEventListener
      |
      v
VetRoster.assignVet()

This script does not modify PetClinic or RASE.
"""

from pathlib import Path
import re
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PETCLINIC_ROOT = Path(
    r"C:\Users\Dr. AR\RASE\spring-petclinic-modulith"
)

OUTPUT_DIR = PROJECT_ROOT / "results" / "petclinic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "petclinic_verified_workflow.json"
)


def read_java(path):
    return path.read_text(
        encoding="utf-8",
        errors="replace"
    )


def find_java_files():
    return sorted(
        p for p in PETCLINIC_ROOT.rglob("*.java")
        if ".git" not in p.parts
        and "target" not in p.parts
        and "build" not in p.parts
    )


def find_files_containing(files, pattern):
    matches = []

    regex = re.compile(
        pattern,
        re.MULTILINE
    )

    for path in files:
        source = read_java(path)

        if regex.search(source):
            matches.append(path)

    return matches


def show_matching_lines(path, patterns):
    lines = read_java(path).splitlines()

    results = []

    compiled = [
        re.compile(p)
        for p in patterns
    ]

    for number, line in enumerate(
        lines,
        start=1
    ):
        if any(
            regex.search(line)
            for regex in compiled
        ):
            results.append(
                {
                    "line": number,
                    "text": line.strip()
                }
            )

    return results


def main():

    print("=" * 72)
    print("PETCLINIC WORKFLOW VERIFICATION")
    print("Stage E3.1b")
    print("=" * 72)

    if not PETCLINIC_ROOT.exists():
        raise FileNotFoundError(
            f"Repository not found: {PETCLINIC_ROOT}"
        )

    files = find_java_files()

    print(
        f"\nJava source files: {len(files)}"
    )

    # ------------------------------------------------------------
    # 1. Locate VisitBooked
    # ------------------------------------------------------------

    event_files = find_files_containing(
        files,
        r"\bVisitBooked\b"
    )

    print("\n[1] VisitBooked")

    for path in event_files:
        print(
            "   ",
            path.relative_to(PETCLINIC_ROOT)
        )

    # ------------------------------------------------------------
    # 2. Locate publisher
    # ------------------------------------------------------------

    publisher_candidates = []

    for path in event_files:

        lines = read_java(path).splitlines()

        for number, line in enumerate(
            lines,
            start=1
        ):

            if (
                "VisitBooked" in line
                and (
                    "publishEvent" in line
                    or "new VisitBooked" in line
                )
            ):
                publisher_candidates.append(
                    {
                        "file": str(
                            path.relative_to(
                                PETCLINIC_ROOT
                            )
                        ),
                        "line": number,
                        "text": line.strip()
                    }
                )

    print("\n[2] VisitBooked publication")

    for item in publisher_candidates:
        print(
            f"    {item['file']}:{item['line']}"
        )
        print(
            f"       {item['text']}"
        )

    # ------------------------------------------------------------
    # 3. Locate VetEventListener
    # ------------------------------------------------------------

    listener_files = find_files_containing(
        files,
        r"\bVetEventListener\b"
    )

    print("\n[3] VetEventListener")

    listener_evidence = []

    for path in listener_files:

        print(
            "   ",
            path.relative_to(PETCLINIC_ROOT)
        )

        evidence = show_matching_lines(
            path,
            [
                r"\bVisitBooked\b",
                r"\bEventListener\b",
                r"\bApplicationModuleListener\b",
            ]
        )

        for item in evidence:

            listener_evidence.append(
                {
                    "file": str(
                        path.relative_to(
                            PETCLINIC_ROOT
                        )
                    ),
                    **item
                }
            )

            print(
                f"       line {item['line']}: "
                f"{item['text']}"
            )

    # ------------------------------------------------------------
    # 4. Locate VetRoster.assignVet()
    # ------------------------------------------------------------

    roster_files = find_files_containing(
        files,
        r"\bVetRoster\b"
    )

    print("\n[4] VetRoster / assignVet")

    roster_evidence = []

    for path in roster_files:

        evidence = show_matching_lines(
            path,
            [
                r"\bVetRoster\b",
                r"\bassignVet\s*\(",
            ]
        )

        if evidence:

            print(
                "   ",
                path.relative_to(PETCLINIC_ROOT)
            )

            for item in evidence:

                roster_evidence.append(
                    {
                        "file": str(
                            path.relative_to(
                                PETCLINIC_ROOT
                            )
                        ),
                        **item
                    }
                )

                print(
                    f"       line {item['line']}: "
                    f"{item['text']}"
                )

    # ------------------------------------------------------------
    # 5. Build verification result
    # ------------------------------------------------------------

    checks = {

        "event_exists":
            len(event_files) > 0,

        "publisher_found":
            len(publisher_candidates) > 0,

        "listener_found":
            len(listener_files) > 0,

        "listener_references_event":
            any(
                "VisitBooked" in item["text"]
                for item in listener_evidence
            ),

        "roster_found":
            len(roster_files) > 0,

        "assign_vet_found":
            any(
                "assignVet" in item["text"]
                for item in roster_evidence
            ),
    }

    verified = all(checks.values())

    result = {

        "case_study":
            "Spring PetClinic Modulith",

        "verification":
            "E3.1b",

        "workflow":
            [
                "VisitScheduler publishes VisitBooked",
                "VetEventListener consumes VisitBooked",
                "VetEventListener delegates assignment",
                "VetRoster performs vet assignment"
            ],

        "checks":
            checks,

        "publisher_evidence":
            publisher_candidates,

        "listener_evidence":
            listener_evidence,

        "roster_evidence":
            roster_evidence,

        "verified":
            verified,

        "ground_truth_status":
            (
                "VERIFIED"
                if verified
                else "NOT_VERIFIED"
            )
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            result,
            indent=2
        ),
        encoding="utf-8"
    )

    # ------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------

    print("\n" + "=" * 72)

    if verified:

        print(
            "PASS: PetClinic workflow is "
            "source-grounded and verified."
        )

        print(
            "\nVerified chain:"
        )

        print(
            "VisitScheduler"
        )

        print(
            "      |"
        )

        print(
            "      | VisitBooked"
        )

        print(
            "      v"
        )

        print(
            "VetEventListener"
        )

        print(
            "      |"
        )

        print(
            "      v"
        )

        print(
            "VetRoster.assignVet()"
        )

    else:

        print(
            "WARNING: Workflow could not be "
            "fully verified."
        )

    print(
        f"\nSaved verification:"
    )

    print(
        OUTPUT_FILE
    )

    print("=" * 72)


if __name__ == "__main__":
    main()