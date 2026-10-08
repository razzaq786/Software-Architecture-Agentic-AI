from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
import math


def now_utc():
    return datetime.now(timezone.utc)


def parse_timestamp(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    # Ensure comparisons remain timezone-aware.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


@dataclass
class Evidence:
    agent_id: str
    capability: str
    outcome: str
    support: float
    timestamp: str
    source: str = "runtime"
    evidence_id: Optional[str] = None


class EAS:
    """
    Evidence-Assessed Architectural State (EAS).

    EAS estimates the assurance of an architectural fact from
    freshness-weighted runtime/historical evidence.

    The implementation deliberately separates:

    1. Outcome consistency
       How strongly the available evidence supports SUCCESS
       relative to negative observations.

    2. Evidence strength
       How much effective evidence is actually available.

    This prevents a single weak positive observation, for example
    support=0.25, from becoming assurance=1.0 merely because no
    negative observation exists.

    E2 additionally models:

    - evidence freshness
    - contradictory evidence
    - evidence strength
    - explicit uncertainty
    - stale evidence
    - freshness-weighted assurance
    """

    POSITIVE_OUTCOMES = {
        "SUCCESS",
    }

    NEGATIVE_OUTCOMES = {
        "FAILURE",
        "UNAVAILABLE",
        "DEGRADED",
    }

    def __init__(
        self,
        freshness_half_life_seconds=60.0,
        uncertainty_threshold=0.75,
        conflict_threshold=0.20,
        stale_threshold=0.25,
    ):
        self.evidence: List[Evidence] = []

        self.freshness_half_life_seconds = (
            float(freshness_half_life_seconds)
        )

        self.uncertainty_threshold = (
            float(uncertainty_threshold)
        )

        self.conflict_threshold = (
            float(conflict_threshold)
        )

        self.stale_threshold = (
            float(stale_threshold)
        )

    # ------------------------------------------------------------------
    # Evidence management
    # ------------------------------------------------------------------

    def add_evidence(
        self,
        agent_id,
        capability,
        outcome,
        support,
        timestamp=None,
        source="runtime",
        evidence_id=None,
    ):
        """
        Add one evidence observation.

        support is constrained to [0, 1].

        1.0 = full-strength observation
        0.25 = weak observation
        0.0 = no effective support
        """

        if timestamp is None:
            timestamp = now_utc().isoformat()

        try:
            support = float(support)
        except (TypeError, ValueError):
            raise ValueError(
                "Evidence support must be numeric."
            )

        support = max(
            0.0,
            min(1.0, support),
        )

        outcome = str(outcome).upper()

        record = Evidence(
            agent_id=agent_id,
            capability=capability,
            outcome=outcome,
            support=support,
            timestamp=timestamp,
            source=source,
            evidence_id=evidence_id,
        )

        self.evidence.append(record)

    def get_evidence(
        self,
        agent_id,
        capability,
    ):
        return [
            e
            for e in self.evidence
            if e.agent_id == agent_id
            and e.capability == capability
        ]

    # ------------------------------------------------------------------
    # Freshness
    # ------------------------------------------------------------------

    def freshness_weight(
        self,
        evidence,
        reference_time=None,
    ):
        """
        Exponential freshness decay.

        A half-life of H means the evidence contribution
        becomes half as strong every H seconds.
        """

        if reference_time is None:
            reference_time = now_utc()

        reference_time = parse_timestamp(
            reference_time
        )

        timestamp = parse_timestamp(
            evidence.timestamp
        )

        age = max(
            0.0,
            (
                reference_time - timestamp
            ).total_seconds(),
        )

        if self.freshness_half_life_seconds <= 0:
            return 1.0

        return math.exp(
            -math.log(2.0)
            * age
            / self.freshness_half_life_seconds
        )

    def freshness(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Returns the freshness of the most recent evidence.

        1.0 = completely fresh
        values approaching 0 = very stale
        """

        records = self.get_evidence(
            agent_id,
            capability,
        )

        if not records:
            return 0.0

        return max(
            self.freshness_weight(
                evidence,
                reference_time,
            )
            for evidence in records
        )

    def is_stale(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        return (
            self.freshness(
                agent_id,
                capability,
                reference_time,
            )
            < self.stale_threshold
        )

    # ------------------------------------------------------------------
    # Weighted evidence
    # ------------------------------------------------------------------

    def _weighted_evidence(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Returns freshness-weighted positive and negative
        evidence masses.
        """

        records = self.get_evidence(
            agent_id,
            capability,
        )

        positive = 0.0
        negative = 0.0

        for evidence in records:

            freshness = self.freshness_weight(
                evidence,
                reference_time,
            )

            effective_support = (
                evidence.support
                * freshness
            )

            if (
                evidence.outcome
                in self.POSITIVE_OUTCOMES
            ):
                positive += effective_support

            elif (
                evidence.outcome
                in self.NEGATIVE_OUTCOMES
            ):
                negative += effective_support

        return positive, negative

    def positive_weight(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        positive, _ = self._weighted_evidence(
            agent_id,
            capability,
            reference_time,
        )
        return positive

    def negative_weight(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        _, negative = self._weighted_evidence(
            agent_id,
            capability,
            reference_time,
        )
        return negative

    def total_effective_evidence(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        positive, negative = self._weighted_evidence(
            agent_id,
            capability,
            reference_time,
        )

        return positive + negative

    # ------------------------------------------------------------------
    # Evidence strength
    # ------------------------------------------------------------------

    def evidence_strength(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Measures how much effective evidence is available.

        The value is bounded to [0, 1].

        This is intentionally different from outcome consistency.

        Examples:

            SUCCESS support=1.0
                -> strength=1.0

            SUCCESS support=0.25
                -> strength=0.25

            SUCCESS support=1.0, stale by 50%
                -> strength=0.5

        Thus weak or stale evidence cannot automatically produce
        full architectural assurance.
        """

        total = self.total_effective_evidence(
            agent_id,
            capability,
            reference_time,
        )

        return max(
            0.0,
            min(1.0, total),
        )

    # ------------------------------------------------------------------
    # Assurance
    # ------------------------------------------------------------------

    def assurance(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Compute evidence-assessed assurance.

        Assurance =
            outcome consistency
            × evidence strength

        Outcome consistency:
            positive / (positive + negative)

        Evidence strength:
            min(1, total effective evidence)

        This gives a conservative interpretation of evidence:
        strong and consistent evidence is required for high
        assurance.
        """

        positive, negative = self._weighted_evidence(
            agent_id,
            capability,
            reference_time,
        )

        total = positive + negative

        if total <= 0:
            return 0.0

        outcome_consistency = (
            positive / total
        )

        strength = self.evidence_strength(
            agent_id,
            capability,
            reference_time,
        )

        assurance = (
            outcome_consistency
            * strength
        )

        return max(
            0.0,
            min(1.0, assurance),
        )

    # ------------------------------------------------------------------
    # Contradiction
    # ------------------------------------------------------------------

    def contradiction_score(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Measures the degree to which evidence contains both
        positive and negative observations.

        0.0 = no contradiction
        0.5 = balanced positive/negative evidence

        The metric is based on freshness-weighted evidence.
        """

        positive, negative = self._weighted_evidence(
            agent_id,
            capability,
            reference_time,
        )

        total = positive + negative

        if total <= 0:
            return 0.0

        return min(
            positive,
            negative,
        ) / total

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(
        self,
        agent_id,
        capability,
        reference_time=None,
    ):
        """
        Classify the current evidence state.

        ASSURED:
            sufficient and consistent evidence.

        UNCERTAIN_CONFLICT:
            meaningful contradictory evidence.

        UNCERTAIN:
            insufficient, weak, or stale evidence.
        """

        assurance = self.assurance(
            agent_id,
            capability,
            reference_time,
        )

        contradiction = self.contradiction_score(
            agent_id,
            capability,
            reference_time,
        )

        if contradiction >= self.conflict_threshold:
            return "UNCERTAIN_CONFLICT"

        if self.is_stale(
            agent_id,
            capability,
            reference_time,
        ):
            return "UNCERTAIN"

        if assurance < self.uncertainty_threshold:
            return "UNCERTAIN"

        return "ASSURED"

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def evidence_count(
        self,
        agent_id,
        capability,
    ):
        return len(
            self.get_evidence(
                agent_id,
                capability,
            )
        )

    def print_assurance(
        self,
        agent_id,
        capability,
    ):
        assurance = self.assurance(
            agent_id,
            capability,
        )

        contradiction = self.contradiction_score(
            agent_id,
            capability,
        )

        freshness = self.freshness(
            agent_id,
            capability,
        )

        strength = self.evidence_strength(
            agent_id,
            capability,
        )

        status = self.status(
            agent_id,
            capability,
        )

        print(
            f"{agent_id} / {capability}: "
            f"assurance={assurance:.3f}, "
            f"strength={strength:.3f}, "
            f"freshness={freshness:.3f}, "
            f"contradiction={contradiction:.3f}, "
            f"status={status}, "
            f"evidence={self.evidence_count(agent_id, capability)}"
        )