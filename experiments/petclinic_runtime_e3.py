from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PILOT_ROOT = Path(__file__).resolve().parents[1]
PETCLINIC_ROOT = Path(r"C:\Users\Dr. AR\RASE\spring-petclinic-modulith")

RESULTS_DIR = PILOT_ROOT / "results" / "petclinic"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ACTUATOR_URL = "http://localhost:8080/actuator/modulith"

# ---------------------------------------------------------------------
# Import RASE
# ---------------------------------------------------------------------

sys.path.insert(0, str(PILOT_ROOT))

from rase.rase_runtime import RASERuntime


# ---------------------------------------------------------------------
# Runtime observation
# ---------------------------------------------------------------------

def fetch_runtime_modulith(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "RASE-E3.3-Runtime-Observer",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return {
                "status_code": response.status,
                "payload": json.loads(payload),
            }

    except HTTPError as exc:
        raise RuntimeError(
            f"PetClinic actuator returned HTTP {exc.code}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Could not connect to PetClinic actuator: {exc.reason}"
        ) from exc


# ---------------------------------------------------------------------
# Parse Spring Modulith runtime architecture
# ---------------------------------------------------------------------

def parse_runtime_architecture(payload: dict) -> dict:
    modules = []
    dependencies = []

    for module_id, module_data in payload.items():
        modules.append(
            {
                "module_id": module_id,
                "display_name": module_data.get(
                    "displayName",
                    module_id,
                ),
                "base_package": module_data.get(
                    "basePackage",
                    "",
                ),
                "type": module_data.get(
                    "type",
                    "",
                ),
                "shared": module_data.get(
                    "shared",
                    False,
                ),
            }
        )

        for dependency in module_data.get(
            "dependencies",
            [],
        ):
            target = dependency.get("target")

            for dependency_type in dependency.get(
                "types",
                [],
            ):
                dependencies.append(
                    {
                        "source": module_id,
                        "target": target,
                        "relation_type": dependency_type,
                    }
                )

    return {
        "modules": modules,
        "dependencies": dependencies,
    }


# ---------------------------------------------------------------------
# Source-grounded architecture
#
# This comes from the previously verified source inspection:
#
# VisitScheduler
#      |
#      | publishes VisitBooked
#      v
# VetEventListener
#      |
#      | delegates
#      v
# VetRoster.assignVet()
#
# At module level this corresponds to:
#
# Vet <--- EVENT_LISTENER --- Owner
# ---------------------------------------------------------------------

SOURCE_MODULE_DEPENDENCIES = {
    (
        "vet",
        "owner",
        "EVENT_LISTENER",
    )
}

SOURCE_WORKFLOW = [
    {
        "source": "VisitScheduler",
        "relation": "publishes",
        "target": "VisitBooked",
    },
    {
        "source": "VetEventListener",
        "relation": "consumes",
        "target": "VisitBooked",
    },
    {
        "source": "VetEventListener",
        "relation": "delegates-to",
        "target": "VetRoster.assignVet",
    },
]


# ---------------------------------------------------------------------
# Runtime/source comparison
# ---------------------------------------------------------------------

def compare_architectures(runtime_architecture: dict) -> dict:
    runtime_dependencies = {
        (
            item["source"],
            item["target"],
            item["relation_type"],
        )
        for item in runtime_architecture["dependencies"]
    }

    source_dependencies = SOURCE_MODULE_DEPENDENCIES

    matched = runtime_dependencies.intersection(
        source_dependencies
    )

    runtime_only = runtime_dependencies - source_dependencies
    source_only = source_dependencies - runtime_dependencies

    if source_dependencies:
        dependency_recall = (
            len(matched) / len(source_dependencies)
        )
    else:
        dependency_recall = 1.0

    if runtime_dependencies:
        dependency_precision = (
            len(matched) / len(runtime_dependencies)
        )
    else:
        dependency_precision = 1.0

    if dependency_precision + dependency_recall > 0:
        dependency_f1 = (
            2
            * dependency_precision
            * dependency_recall
            / (dependency_precision + dependency_recall)
        )
    else:
        dependency_f1 = 0.0

    return {
        "source_dependency_count": len(source_dependencies),
        "runtime_dependency_count": len(runtime_dependencies),
        "matched_dependency_count": len(matched),
        "runtime_only_count": len(runtime_only),
        "source_only_count": len(source_only),
        "dependency_precision": dependency_precision,
        "dependency_recall": dependency_recall,
        "dependency_f1": dependency_f1,
        "runtime_matches_source": (
            runtime_dependencies == source_dependencies
        ),
        "matched_dependencies": sorted(
            [
                {
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                }
                for source, target, relation_type in matched
            ],
            key=lambda x: (
                x["source"],
                x["target"],
                x["relation_type"],
            ),
        ),
        "runtime_only_dependencies": sorted(
            [
                {
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                }
                for source, target, relation_type in runtime_only
            ],
            key=lambda x: (
                x["source"],
                x["target"],
                x["relation_type"],
            ),
        ),
        "source_only_dependencies": sorted(
            [
                {
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                }
                for source, target, relation_type in source_only
            ],
            key=lambda x: (
                x["source"],
                x["target"],
                x["relation_type"],
            ),
        ),
    }


# ---------------------------------------------------------------------
# RASE mapping
# ---------------------------------------------------------------------

def build_rase_runtime(runtime_architecture: dict) -> dict:
    runtime = RASERuntime()

    # Register runtime-observed modules as architectural entities.
    #
    # The /actuator/modulith endpoint provides module-level
    # architectural information. It does not provide method-level
    # agent information, so we preserve that distinction here.
    registered_modules = set()

    for module in runtime_architecture["modules"]:
        module_id = module["module_id"]

        capability = f"module:{module_id}"
        responsibility = f"runtime-module:{module_id}"

        runtime.register_agent(
            module_id,
            capability,
            responsibility,
        )

        registered_modules.add(module_id)

    # Map runtime module dependencies into TSDM.
    relation_map = {
        "EVENT_LISTENER": "supports-responsibility",
    }

    mapped_dependencies = []

    for dependency in runtime_architecture["dependencies"]:
        source = dependency["source"]
        target = dependency["target"]

        if source not in registered_modules:
            continue

        if target not in registered_modules:
            continue

        relation_type = relation_map.get(
            dependency["relation_type"],
            "supports-responsibility",
        )

        runtime.add_dependency(
            source,
            target,
            relation_type,
        )

        mapped_dependencies.append(
            {
                "source": source,
                "target": target,
                "source_relation": dependency["relation_type"],
                "rase_relation": relation_type,
            }
        )

    # -------------------------------------------------------------
    # Runtime architectural evidence
    # -------------------------------------------------------------
    #
    # RASERuntime.add_evidence() is intentionally used with its
    # confirmed public API:
    #
    #     add_evidence(agent_id, capability, outcome, support)
    #
    # Timestamp/source provenance is retained separately in the
    # E3.3 experiment record because the runtime wrapper does not
    # expose those arguments.
    #
    timestamp = datetime.now(timezone.utc).isoformat()

    evidence_records = []

    for dependency in runtime_architecture["dependencies"]:
        source = dependency["source"]
        target = dependency["target"]
        runtime_relation = dependency["relation_type"]

        capability = (
            f"runtime-dependency:"
            f"{source}->{target}:"
            f"{runtime_relation}"
        )

        # Use the confirmed RASERuntime API.
        runtime.add_evidence(
            source,
            capability,
            "SUCCESS",
            1.0,
        )

        evidence_records.append(
            {
                "agent_id": source,
                "capability": capability,
                "outcome": "SUCCESS",
                "support": 1.0,
                "timestamp": timestamp,
                "source": "petclinic-actuator-modulith",
                "target": target,
                "runtime_relation": runtime_relation,
            }
        )

    return {
        "runtime": runtime,
        "mapped_dependencies": mapped_dependencies,
        "evidence_records": evidence_records,
    }


# ---------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------

def print_report(
    runtime_response: dict,
    runtime_architecture: dict,
    comparison: dict,
    rase_mapping: dict,
) -> None:

    print("=" * 72)
    print("PETCLINIC RUNTIME ARCHITECTURE OBSERVATION")
    print("E3.3: ACTUAL SPRING MODULITH RUNTIME -> RASE")
    print("=" * 72)

    print()
    print(f"Actuator endpoint : {ACTUATOR_URL}")
    print(
        f"HTTP status       : "
        f"{runtime_response['status_code']}"
    )

    print()
    print("-" * 72)
    print("RUNTIME MODULES")
    print("-" * 72)

    for module in runtime_architecture["modules"]:
        print(
            f"  {module['module_id']:10s} "
            f"{module['display_name']}"
        )

    print()
    print("-" * 72)
    print("RUNTIME DEPENDENCIES")
    print("-" * 72)

    if not runtime_architecture["dependencies"]:
        print("  NONE")
    else:
        for dependency in runtime_architecture["dependencies"]:
            print(
                f"  {dependency['source']} "
                f"--{dependency['relation_type']}--> "
                f"{dependency['target']}"
            )

    print()
    print("-" * 72)
    print("SOURCE / RUNTIME CONSISTENCY")
    print("-" * 72)

    print(
        f"  Source dependencies : "
        f"{comparison['source_dependency_count']}"
    )
    print(
        f"  Runtime dependencies: "
        f"{comparison['runtime_dependency_count']}"
    )
    print(
        f"  Matched             : "
        f"{comparison['matched_dependency_count']}"
    )
    print(
        f"  Precision           : "
        f"{comparison['dependency_precision']:.3f}"
    )
    print(
        f"  Recall              : "
        f"{comparison['dependency_recall']:.3f}"
    )
    print(
        f"  F1                  : "
        f"{comparison['dependency_f1']:.3f}"
    )
    print(
        f"  Exact consistency   : "
        f"{comparison['runtime_matches_source']}"
    )

    if comparison["runtime_only_dependencies"]:
        print()
        print("  Runtime-only dependencies:")
        for item in comparison["runtime_only_dependencies"]:
            print(
                f"    {item['source']} "
                f"--{item['relation_type']}--> "
                f"{item['target']}"
            )

    if comparison["source_only_dependencies"]:
        print()
        print("  Source-only dependencies:")
        for item in comparison["source_only_dependencies"]:
            print(
                f"    {item['source']} "
                f"--{item['relation_type']}--> "
                f"{item['target']}"
            )

    print()
    print("-" * 72)
    print("RASE MAPPING")
    print("-" * 72)

    print(
        f"  ERAM runtime entities : "
        f"{len(runtime_architecture['modules'])}"
    )
    print(
        f"  TSDM dependencies     : "
        f"{len(rase_mapping['mapped_dependencies'])}"
    )
    print(
        f"  EAS evidence records  : "
        f"{len(rase_mapping['evidence_records'])}"
    )

    print()
    print("  Mapped TSDM relationships:")

    for item in rase_mapping["mapped_dependencies"]:
        print(
            f"    {item['source']} "
            f"--{item['rase_relation']}--> "
            f"{item['target']} "
            f"[{item['source_relation']}]"
        )

    print()
    print("=" * 72)

    if comparison["runtime_matches_source"]:
        print(
            "PASS: Runtime architecture is consistent with "
            "the verified source-level module dependency."
        )
    else:
        print(
            "WARNING: Runtime and source architectures differ; "
            "inspect the recorded differences."
        )

    print("=" * 72)


# ---------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------

def save_results(
    runtime_response: dict,
    runtime_architecture: dict,
    comparison: dict,
    rase_mapping: dict,
) -> None:

    timestamp = datetime.now(timezone.utc).isoformat()

    result = {
        "experiment": "E3.3",
        "experiment_name": (
            "Actual PetClinic Runtime Architecture Observation"
        ),
        "timestamp_utc": timestamp,
        "application": "Spring PetClinic Modulith",
        "actuator_endpoint": ACTUATOR_URL,
        "http_status": runtime_response["status_code"],
        "runtime_architecture": runtime_architecture,
        "source_workflow": SOURCE_WORKFLOW,
        "source_module_dependencies": [
            {
                "source": source,
                "target": target,
                "relation_type": relation_type,
            }
            for source, target, relation_type
            in sorted(SOURCE_MODULE_DEPENDENCIES)
        ],
        "comparison": comparison,
        "rase_mapping": {
            "mapped_dependencies":
                rase_mapping["mapped_dependencies"],
            "evidence_records":
                rase_mapping["evidence_records"],
        },
    }

    json_path = (
        RESULTS_DIR /
        "petclinic_runtime_e3_results.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            indent=2,
        )

    csv_path = (
        RESULTS_DIR /
        "petclinic_runtime_e3_dependencies.csv"
    )

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source",
                "target",
                "runtime_relation",
                "rase_relation",
                "matched_source_dependency",
            ],
        )

        writer.writeheader()

        source_dependency_set = (
            SOURCE_MODULE_DEPENDENCIES
        )

        for dependency in runtime_architecture[
            "dependencies"
        ]:

            key = (
                dependency["source"],
                dependency["target"],
                dependency["relation_type"],
            )

            rase_relation = "supports-responsibility"

            writer.writerow(
                {
                    "source": dependency["source"],
                    "target": dependency["target"],
                    "runtime_relation":
                        dependency["relation_type"],
                    "rase_relation":
                        rase_relation,
                    "matched_source_dependency":
                        key in source_dependency_set,
                }
            )

    raw_path = (
        RESULTS_DIR /
        "petclinic_runtime_modulith_raw.json"
    )

    with open(
        raw_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            runtime_response["payload"],
            file,
            indent=2,
        )

    print()
    print("Generated files:")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    print(f"  {raw_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:

    print(
        "Checking running PetClinic "
        "runtime endpoint..."
    )

    runtime_response = fetch_runtime_modulith(
        ACTUATOR_URL
    )

    runtime_architecture = parse_runtime_architecture(
        runtime_response["payload"]
    )

    comparison = compare_architectures(
        runtime_architecture
    )

    rase_mapping = build_rase_runtime(
        runtime_architecture
    )

    print_report(
        runtime_response,
        runtime_architecture,
        comparison,
        rase_mapping,
    )

    save_results(
        runtime_response,
        runtime_architecture,
        comparison,
        rase_mapping,
    )


if __name__ == "__main__":
    main()