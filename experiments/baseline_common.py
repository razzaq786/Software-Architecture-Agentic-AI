from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GroundTruth:
    scenario: str

    # Architectural impact expected from the triggering event.
    affected_agents: List[str]

    # Structurally/functionally valid replacement, if one exists.
    valid_replacement: Optional[str]

    # Whether autonomous commitment is semantically correct.
    replacement_should_commit: bool

    # Expected final functional architecture.
    expected_final_architecture: str

    # Expected system-level decision.
    expected_decision: str

    # Whether the scenario contains a replacement candidate.
    replacement_available: bool

    # Whether the candidate has sufficient evidence for autonomous commitment.
    evidence_sufficient: bool


SCENARIOS = {
    "S0_NORMAL": GroundTruth(
        scenario="S0_NORMAL",
        affected_agents=[],
        valid_replacement=None,
        replacement_should_commit=False,
        expected_final_architecture="A1->A2->A3",
        expected_decision="NO_ADAPTATION",
        replacement_available=False,
        evidence_sufficient=True,
    ),

    "S1_REPLACEMENT_PASS": GroundTruth(
        scenario="S1_REPLACEMENT_PASS",
        affected_agents=["A2", "A3"],
        valid_replacement="A2_prime",
        replacement_should_commit=True,
        expected_final_architecture="A1->A2_prime->A3",
        expected_decision="COMMIT",
        replacement_available=True,
        evidence_sufficient=True,
    ),

    "S2_REPLACEMENT_FAIL": GroundTruth(
        scenario="S2_REPLACEMENT_FAIL",
        affected_agents=["A2", "A3"],
        valid_replacement="A2_prime",
        replacement_should_commit=False,
        expected_final_architecture="A1->A2->A3",
        expected_decision="ROLLBACK",
        replacement_available=True,
        evidence_sufficient=True,
    ),

    "S3_NO_REPLACEMENT": GroundTruth(
        scenario="S3_NO_REPLACEMENT",
        affected_agents=["A2", "A3"],
        valid_replacement=None,
        replacement_should_commit=False,
        expected_final_architecture="A1->A2->A3",
        expected_decision="NO_REPLACEMENT",
        replacement_available=False,
        evidence_sufficient=False,
    ),

    "S4_IRRELEVANT_BRANCH": GroundTruth(
        scenario="S4_IRRELEVANT_BRANCH",
        affected_agents=["A2", "A3"],
        valid_replacement=None,
        replacement_should_commit=False,
        expected_final_architecture="A1->A2->A3|A4->A2",
        expected_decision="NO_REPLACEMENT",
        replacement_available=False,
        evidence_sufficient=False,
    ),

    "S5_UNCERTAIN_REPLACEMENT_EVIDENCE": GroundTruth(
        scenario="S5_UNCERTAIN_REPLACEMENT_EVIDENCE",
        affected_agents=["A2", "A3"],
        valid_replacement="A2_prime",
        replacement_should_commit=False,
        expected_final_architecture="A1->A2->A3|A4->A2",
        expected_decision="DEFER_UNCERTAIN",
        replacement_available=True,
        evidence_sufficient=False,
    ),
}