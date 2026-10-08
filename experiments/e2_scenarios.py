from datetime import datetime, timedelta, timezone


def utc_now():
    return datetime.now(timezone.utc)


def timestamp_seconds_ago(seconds):
    return (
        utc_now() - timedelta(seconds=seconds)
    ).isoformat()


def timestamp_minutes_ago(minutes):
    return timestamp_seconds_ago(minutes * 60)


def configure_s6_stale_evidence(runtime):
    """
    S6: The available agent has only stale positive evidence.
    """

    runtime.eas.evidence.clear()

    runtime.add_historical_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0,
        timestamp_minutes_ago(10),
    )


def configure_s7_contradictory_evidence(runtime):
    """
    S7: Fresh evidence contains both successful and failed
    observations, producing an uncertain/conflicting state.
    """

    runtime.eas.evidence.clear()

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0,
    )

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "FAILURE",
        1.0,
    )


def configure_s8_initial_state(runtime):
    """
    S8 initial condition: A2 is supported by fresh successful
    evidence. No failure observation has arrived yet.
    """

    runtime.eas.evidence.clear()

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0,
    )


def configure_s8_delayed_observation(runtime):
    """
    S8 delayed condition: the failure/unavailability observation
    arrives only after the initial assured state.
    """

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "UNAVAILABLE",
        1.0,
    )


def configure_s9_degraded_agent(runtime):
    """
    S9: A2 has both successful and degraded observations.
    The resulting evidence state should be treated as uncertain.
    """

    runtime.eas.evidence.clear()

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "SUCCESS",
        1.0,
    )

    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "DEGRADED",
        1.0,
    )


def configure_s10_weak_replacement(runtime):
    """
    S10: A2 has failed, while A2_prime is operationally available
    but supported only by weak evidence.

    The candidate replacement therefore must not be committed
    until sufficient evidence is available.
    """

    runtime.eas.evidence.clear()

    # Primary agent failure.
    runtime.add_evidence(
        "A2",
        "VetAssignment",
        "FAILURE",
        1.0,
    )

    # Weak evidence for the candidate replacement.
    #
    # EAS assurance threshold = 0.75.
    # Candidate assurance = 0.25.
    # Therefore the candidate must be rejected/deferred.
    runtime.add_evidence(
        "A2_prime",
        "VetAssignment",
        "SUCCESS",
        0.25,
    )