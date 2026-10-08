
"""
PetClinic-Grounded RASE Case Study — Stage E3.1

Purpose:
    1. Inspect the actual Spring PetClinic Modulith source code.
    2. Locate the VisitBooked event and its publisher/listener.
    3. Locate the downstream vet-assignment logic.
    4. Build a source-grounded workflow manifest.
    5. Export architecture evidence for the RASE case study.

This script does not modify PetClinic or the existing E1/E2 experiments.
It extracts source evidence; it does not claim to execute the Java workflow.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from datetime import datetime, timezone


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PETCLINIC_ROOT = Path(
    r"C:\Users\Dr. AR\RASE\spring-petclinic-modulith"
)

OUTPUT_DIR = PROJECT_ROOT / "results" / "petclinic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_JSON = OUTPUT_DIR / "petclinic_architecture.json"
MANIFEST_CSV = OUTPUT_DIR / "petclinic_architecture.csv"
EVIDENCE_CSV = OUTPUT_DIR / "petclinic_source_evidence.csv"


# ------------------------------------------------------------
# Search helpers
# ------------------------------------------------------------

def java_files(root: Path) -> list[Path]:
    """Return Java source files below the repository."""

    if not root.exists():
        raise FileNotFoundError(
            f"PetClinic repository not found: {root}"
        )

    ignored = {
        ".git",
        "target",
        "build",
        ".gradle",
        "node_modules",
    }

    files = []

    for path in root.rglob("*.java"):
        if any(part in ignored for part in path.parts):
            continue

        files.append(path)

    return sorted(files)


def read_source(path: Path) -> str:
    """Read Java source while tolerating unusual encodings."""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def locate_symbol(files: list[Path], patterns: list[str]):
    """
    Find source files containing any supplied regular expression.
    Returns one result per matching file.
    """

    matches = []

    for path in files:
        source = read_source(path)

        matched_patterns = [
            pattern
            for pattern in patterns
            if re.search(
                pattern,
                source,
                flags=re.MULTILINE,
            )
        ]

        if matched_patterns:
            matches.append(
                {
                    "path": str(path),
                    "relative_path": str(
                        path.relative_to(PETCLINIC_ROOT)
                    ),
                    "patterns": matched_patterns,
                    "source": source,
                }
            )

    return matches


def evidence_lines(
    files: list[Path],
    patterns: list[str],
):
    """
    Extract matching source lines with file and line-number provenance.
    """

    results = []

    for path in files:
        lines = read_source(path).splitlines()

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            if any(
                re.search(pattern, line)
                for pattern in patterns
            ):
                results.append(
                    {
                        "file": str(
                            path.relative_to(PETCLINIC_ROOT)
                        ),
                        "line_number": line_number,
                        "source_line": line.strip(),
                    }
                )

    return results


# ------------------------------------------------------------
# Main extraction
# ------------------------------------------------------------

def main():

    print("=" * 72)
    print("PETCLINIC-GROUNDED RASE CASE STUDY")
    print("Stage E3.1: Source Architecture Extraction")
    print("=" * 72)

    print(f"\nRepository: {PETCLINIC_ROOT}")

    files = java_files(PETCLINIC_ROOT)

    print(f"Java source files found: {len(files)}")

    if not files:
        raise RuntimeError(
            "No Java source files found. "
            "Check the repository path."
        )

    # Search for the concrete workflow symbols.
    event_files = locate_symbol(
        files,
        [
            r"\bVisitBooked\b",
        ],
    )

    publisher_files = locate_symbol(
        files,
        [
            r"\bVisitBooked\b",
            r"\bpublishEvent\s*\(",
            r"\bApplicationEventPublisher\b",
        ],
    )

    listener_files = locate_symbol(
        files,
        [
            r"\bVisitBooked\b",
            r"\bEventListener\b",
            r"\bApplicationModuleListener\b",
        ],
    )

    roster_files = locate_symbol(
        files,
        [
            r"\bVetRoster\b",
            r"\bassignVet\s*\(",
        ],
    )

    assignment_files = locate_symbol(
        files,
        [
            r"\bassignVet\s*\(",
            r"\bVetEventListener\b",
        ],
    )

    # Convert source search results into compact file records.
    def compact(matches):
        return [
            {
                "file": item["relative_path"],
                "matched_patterns": item["patterns"],
            }
            for item in matches
        ]

    # Build a workflow model grounded in source references.
    # Relationships are included as candidate architectural links;
    # the evidence files below let us verify each link.
    components = [
        {
            "id": "OWNER",
            "name": "Owner / VisitScheduler",
            "role": "Visit event publication",
            "source_candidates": compact(publisher_files),
        },
        {
            "id": "VISIT_BOOKED",
            "name": "VisitBooked",
            "role": "Domain event",
            "source_candidates": compact(event_files),
        },
        {
            "id": "VET_LISTENER",
            "name": "VetEventListener",
            "role": "Event consumption",
            "source_candidates": compact(listener_files),
        },
        {
            "id": "VET_ROSTER",
            "name": "VetRoster",
            "role": "Vet assignment",
            "source_candidates": compact(roster_files),
        },
    ]

    relationships = [
        {
            "source": "OWNER",
            "target": "VISIT_BOOKED",
            "relation_type": "produces-event",
            "verification_status": "inspect_source_evidence",
        },
        {
            "source": "VISIT_BOOKED",
            "target": "VET_LISTENER",
            "relation_type": "consumes-event",
            "verification_status": "inspect_source_evidence",
        },
        {
            "source": "VET_LISTENER",
            "target": "VET_ROSTER",
            "relation_type": "delegates-to",
            "verification_status": "inspect_source_evidence",
        },
    ]

    all_evidence = evidence_lines(
        files,
        [
            r"\bVisitBooked\b",
            r"\bpublishEvent\s*\(",
            r"\bVetEventListener\b",
            r"\bVetRoster\b",
            r"\bassignVet\s*\(",
            r"\bEventListener\b",
            r"\bApplicationModuleListener\b",
        ],
    )

    # Identify whether each expected symbol is present.
    all_source = "\n".join(
        read_source(path)
        for path in files
    )

    checks = {
        "VisitBooked_event_found": bool(
            re.search(r"\bVisitBooked\b", all_source)
        ),
        "VetEventListener_found": bool(
            re.search(r"\bVetEventListener\b", all_source)
        ),
        "VetRoster_found": bool(
            re.search(r"\bVetRoster\b", all_source)
        ),
        "assignVet_method_found": bool(
            re.search(r"\bassignVet\s*\(", all_source)
        ),
        "event_publication_reference_found": bool(
            re.search(r"\bpublishEvent\s*\(", all_source)
        ),
    }

    manifest = {
        "experiment": "E3.1",
        "name": "PetClinic-Grounded RASE Architecture",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "repository": str(PETCLINIC_ROOT),
        "java_source_file_count": len(files),
        "scope_note": (
            "Source-derived architecture candidates. "
            "This extraction does not execute PetClinic or prove "
            "runtime behavior. Relationships require source review "
            "and, where applicable, runtime confirmation."
        ),
        "checks": checks,
        "components": components,
        "relationships": relationships,
        "source_evidence": all_evidence,
    }

    # Save JSON manifest.
    MANIFEST_JSON.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Save component and relationship rows.
    architecture_rows = []

    for component in components:
        architecture_rows.append(
            {
                "record_type": "component",
                "id": component["id"],
                "name": component["name"],
                "role": component["role"],
                "source": "; ".join(
                    item["file"]
                    for item in component["source_candidates"]
                ),
                "relation_type": "",
                "target": "",
                "verification_status": "",
            }
        )

    for relationship in relationships:
        architecture_rows.append(
            {
                "record_type": "relationship",
                "id": relationship["source"],
                "name": "",
                "role": "",
                "source": "",
                "relation_type": relationship["relation_type"],
                "target": relationship["target"],
                "verification_status": relationship[
                    "verification_status"
                ],
            }
        )

    with MANIFEST_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "record_type",
                "id",
                "name",
                "role",
                "source",
                "relation_type",
                "target",
                "verification_status",
            ],
        )

        writer.writeheader()
        writer.writerows(architecture_rows)

    # Save source evidence with line numbers.
    with EVIDENCE_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "line_number",
                "source_line",
            ],
        )

        writer.writeheader()
        writer.writerows(all_evidence)

    # Report results.
    print("\n" + "-" * 72)
    print("SOURCE VALIDATION")
    print("-" * 72)

    for name, passed in checks.items():
        status = "FOUND" if passed else "NOT FOUND"
        print(f"{name:40s}: {status}")

    print("\n" + "-" * 72)
    print("ARCHITECTURE EXTRACTION")
    print("-" * 72)

    print(f"Components modeled   : {len(components)}")
    print(f"Relationships modeled: {len(relationships)}")
    print(f"Evidence lines saved : {len(all_evidence)}")

    print("\nGenerated files:")

    print(f"  {MANIFEST_JSON}")
    print(f"  {MANIFEST_CSV}")
    print(f"  {EVIDENCE_CSV}")

    print("\n" + "-" * 72)

    if all(checks.values()):
        print(
            "PASS: All expected workflow symbols were located."
        )
    else:
        print(
            "WARNING: Some expected symbols were not found. "
            "Inspect the evidence and adjust the source mapping "
            "before proceeding."
        )

    print(
        "\nNext: verify the extracted event chain against the actual "
        "source files before using it as experimental ground truth."
    )

    print("=" * 72)


if __name__ == "__main__":
    main()