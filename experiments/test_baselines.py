import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.baseline_common import SCENARIOS
from experiments.baseline_systems import (
    create_agents,
    run_static,
    run_dynamic,
    run_untyped,
    run_rase_no_eas,
    run_rase,
)


SYSTEMS = [
    ("B1_STATIC", run_static),
    ("B2_DYNAMIC", run_dynamic),
    ("B3_UNTYPED", run_untyped),
    ("B4_RASE_NO_EAS", run_rase_no_eas),
    ("B5_RASE", run_rase),
]


def scenario_configuration(scenario):
    """
    Return the controlled experimental configuration for a scenario.

    The configuration is explicitly defined for every scenario so
    that no state can accidentally leak from one scenario to another.
    """

    configurations = {
        "S0_NORMAL": {
            "include_replacement": True,
            "degraded": False,
        },

        "S1_REPLACEMENT_PASS": {
            "include_replacement": True,
            "degraded": False,
        },

        "S2_REPLACEMENT_FAIL": {
            "include_replacement": True,
            "degraded": True,
        },

        "S3_NO_REPLACEMENT": {
            "include_replacement": False,
            "degraded": False,
        },

        "S4_IRRELEVANT_BRANCH": {
            "include_replacement": False,
            "degraded": False,
        },

        "S5_UNCERTAIN_REPLACEMENT_EVIDENCE": {
            "include_replacement": True,
            "degraded": False,
        },
    }

    if scenario not in configurations:
        raise ValueError(f"Unknown scenario: {scenario}")

    return configurations[scenario]


def main():

    print("=" * 70)
    print("BASELINE SMOKE TEST")
    print("=" * 70)

    for scenario in SCENARIOS:

        print(f"\nSCENARIO: {scenario}")
        print("-" * 70)

        config = scenario_configuration(scenario)

        for system_name, system_function in SYSTEMS:

            a1, a2, a2_prime, a3, a4 = create_agents(
                include_replacement=config["include_replacement"],
                degraded_replacement=config["degraded"]
            )

            result = system_function(
                scenario,
                a1,
                a2,
                a2_prime,
                a3,
                a4
            )

            print(
                f"{system_name:20s} "
                f"decision={result['decision']:16s} "
                f"execution={result['execution_success']} "
                f"verification={result['verification_success']} "
                f"reconfig={result['reconfiguration_count']} "
                f"rollback={result['rollback']} "
                f"architecture={result['final_architecture']} "
                f"impact={result.get('impact_set', [])}"
            )

    print("\n" + "=" * 70)
    print("SMOKE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()