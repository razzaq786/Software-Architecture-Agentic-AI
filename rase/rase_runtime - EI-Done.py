from typing import Dict

from .eram import ERAM
from .eas import EAS
from .tsdm import TSDM

#from eram import ERAM
#from eas import EAS
#from tsdm import TSDM


class RASERuntime:

    def __init__(self):
        self.eram = ERAM()
        self.eas = EAS()
        self.tsdm = TSDM()

    # -------------------------------------------------
    # Agent registration
    # -------------------------------------------------

    def register_agent(
        self,
        agent_id,
        capability,
        responsibility
    ):
        self.eram.register_agent(
            agent_id=agent_id,
            capability=capability,
            responsibility=responsibility
        )

    # -------------------------------------------------
    # Architectural dependencies
    # -------------------------------------------------

    def add_dependency(
        self,
        source,
        target,
        relation_type,
        propagation_weight=1.0
    ):
        self.eram.add_dependency(
            source=source,
            target=target,
            relation_type=relation_type,
            assurance=1.0
        )

        self.tsdm.add_dependency(
            source=source,
            target=target,
            relation_type=relation_type,
            propagation_weight=propagation_weight
        )

    # -------------------------------------------------
    # Evidence
    # -------------------------------------------------

    def add_evidence(
        self,
        agent_id,
        capability,
        outcome,
        support
    ):
        self.eas.add_evidence(
            agent_id=agent_id,
            capability=capability,
            outcome=outcome,
            support=support
        )

    def get_assurance(
        self,
        agent_id,
        capability
    ):
        return self.eas.assurance(
            agent_id,
            capability
        )

    def get_all_assurance(self) -> Dict[str, float]:

        assurance = {}

        state = self.eram.get_state()

        for agent_id, agent in state["agents"].items():

            capability = agent["capability"]

            assurance[agent_id] = self.get_assurance(
                agent_id,
                capability
            )

        return assurance

    # -------------------------------------------------
    # Impact analysis
    # -------------------------------------------------

    def analyze_impact(
        self,
        changed_agent
    ):

        assurance = self.get_all_assurance()

        return self.tsdm.propagate_impact(
            changed_agent=changed_agent,
            assurance=assurance
        )

    # -------------------------------------------------
    # Agent status
    # -------------------------------------------------

    def update_agent_status(
        self,
        agent_id,
        status
    ):
        self.eram.update_agent_status(
            agent_id,
            status
        )

    # -------------------------------------------------
    # Failure recording
    # -------------------------------------------------

    def record_agent_failure(
        self,
        agent_id,
        capability,
        support=1.0
    ):

        self.eas.add_evidence(
            agent_id=agent_id,
            capability=capability,
            outcome="FAILURE",
            support=support
        )

        self.update_agent_status(
            agent_id,
            "unavailable"
        )

    # -------------------------------------------------
    # Alternative agent discovery
    # -------------------------------------------------

    def find_alternative_agent(
        self,
        capability,
        responsibility,
        excluded_agent=None
    ):

        state = self.eram.get_state()

        candidates = []

        for agent_id, agent in state["agents"].items():

            if agent_id == excluded_agent:
                continue

            if agent["status"] != "available":
                continue

            if agent["capability"] != capability:
                continue

            if agent["responsibility"] != responsibility:
                continue

            candidates.append(agent_id)

        if not candidates:
            return None

        return candidates[0]

    # -------------------------------------------------
    # Architectural reconfiguration
    # -------------------------------------------------

    def reconfigure_dependency(
        self,
        failed_agent,
        replacement_agent
    ):
        """
        Redirect functional architectural dependencies from a failed
        agent to its replacement.

        ERAM is the authoritative runtime architectural state.
        TSDM is updated in parallel so that impact analysis remains
        consistent with the current architecture.

        Non-functional observational relationships such as 'observes'
        are deliberately preserved.

        Returns a list of architectural transition records used for
        rollback.
        """

        functional_relations = {
            "produces-event",
            "produces-result",
            "supports-responsibility",
            "provides-capability",
            "affects-goal",
        }

        transitions = []

        # Work on a snapshot because both ERAM and TSDM are modified
        # during the reconfiguration.
        eram_dependencies = list(self.eram.dependencies)

        for dependency in eram_dependencies:

            # Outgoing: failed_agent -> target
            if dependency.source == failed_agent:

                if dependency.relation_type not in functional_relations:
                    continue

                old_target = dependency.target
                relation_type = dependency.relation_type
                assurance = dependency.assurance

                # Update ERAM.
                self.eram.remove_dependency(
                    failed_agent,
                    old_target,
                    relation_type
                )

                self.eram.add_dependency(
                    replacement_agent,
                    old_target,
                    relation_type,
                    assurance=assurance
                )

                # Update TSDM.
                tsdm_dependency = next(
                    (
                        d for d in self.tsdm.dependencies
                        if d.source == failed_agent
                        and d.target == old_target
                        and d.relation_type == relation_type
                    ),
                    None
                )

                propagation_weight = (
                    tsdm_dependency.propagation_weight
                    if tsdm_dependency is not None
                    else 1.0
                )

                self.tsdm.remove_dependency(
                    failed_agent,
                    old_target,
                    relation_type
                )

                self.tsdm.add_dependency(
                    replacement_agent,
                    old_target,
                    relation_type,
                    propagation_weight
                )

                transitions.append({
                    "direction": "OUTGOING",
                    "source_old": failed_agent,
                    "source_new": replacement_agent,
                    "target": old_target,
                    "relation_type": relation_type,
                    "propagation_weight": propagation_weight,
                    "assurance": assurance,
                })

            # Incoming: source -> failed_agent
            elif dependency.target == failed_agent:

                if dependency.relation_type not in functional_relations:
                    continue

                old_source = dependency.source
                relation_type = dependency.relation_type
                assurance = dependency.assurance

                # Update ERAM.
                self.eram.remove_dependency(
                    old_source,
                    failed_agent,
                    relation_type
                )

                self.eram.add_dependency(
                    old_source,
                    replacement_agent,
                    relation_type,
                    assurance=assurance
                )

                # Update TSDM.
                tsdm_dependency = next(
                    (
                        d for d in self.tsdm.dependencies
                        if d.source == old_source
                        and d.target == failed_agent
                        and d.relation_type == relation_type
                    ),
                    None
                )

                propagation_weight = (
                    tsdm_dependency.propagation_weight
                    if tsdm_dependency is not None
                    else 1.0
                )

                self.tsdm.remove_dependency(
                    old_source,
                    failed_agent,
                    relation_type
                )

                self.tsdm.add_dependency(
                    old_source,
                    replacement_agent,
                    relation_type,
                    propagation_weight
                )

                transitions.append({
                    "direction": "INCOMING",
                    "source": old_source,
                    "target_old": failed_agent,
                    "target_new": replacement_agent,
                    "relation_type": relation_type,
                    "propagation_weight": propagation_weight,
                    "assurance": assurance,
                })

        return transitions

    # -------------------------------------------------
    # Rollback
    # -------------------------------------------------

    def rollback_reconfiguration(
        self,
        transitions,
        replacement_agent
    ):
        """
        Roll back a previously committed architectural
        reconfiguration in both ERAM and TSDM.

        Observational relationships are not modified.
        """

        for transition in reversed(transitions):

            relation_type = transition["relation_type"]
            propagation_weight = transition["propagation_weight"]
            assurance = transition.get("assurance", 1.0)

            if transition["direction"] == "OUTGOING":

                source_old = transition["source_old"]
                source_new = transition["source_new"]
                target = transition["target"]

                # Restore ERAM.
                self.eram.remove_dependency(
                    source_new,
                    target,
                    relation_type
                )

                self.eram.add_dependency(
                    source_old,
                    target,
                    relation_type,
                    assurance=assurance
                )

                # Restore TSDM.
                self.tsdm.remove_dependency(
                    source_new,
                    target,
                    relation_type
                )

                self.tsdm.add_dependency(
                    source_old,
                    target,
                    relation_type,
                    propagation_weight
                )

            elif transition["direction"] == "INCOMING":

                source = transition["source"]
                target_old = transition["target_old"]
                target_new = transition["target_new"]

                # Restore ERAM.
                self.eram.remove_dependency(
                    source,
                    target_new,
                    relation_type
                )

                self.eram.add_dependency(
                    source,
                    target_old,
                    relation_type,
                    assurance=assurance
                )

                # Restore TSDM.
                self.tsdm.remove_dependency(
                    source,
                    target_new,
                    relation_type
                )

                self.tsdm.add_dependency(
                    source,
                    target_old,
                    relation_type,
                    propagation_weight
                )

        # The replacement is no longer trusted after rollback.
        if replacement_agent in self.eram.agents:
            self.eram.update_agent_status(
                replacement_agent,
                "uncertain"
            )

    # -------------------------------------------------
    # Verification failure recording
    # -------------------------------------------------

    def record_verification_failure(
        self,
        agent_id,
        capability,
        support=1.0
    ):
        """
        Record an independently detected verification
        failure against the agent capability.
        """

        self.eas.add_evidence(
            agent_id=agent_id,
            capability=capability,
            outcome="FAILURE",
            support=support
        )

    # -------------------------------------------------
    # Runtime state display
    # -------------------------------------------------

    def print_state(self):

        print("\n=== RASE RUNTIME STATE ===")

        self.eram.print_state()

        print("\n=== EVIDENCE ASSURANCE ===")

        state = self.eram.get_state()

        for agent_id, agent in state["agents"].items():

            capability = agent["capability"]

            self.eas.print_assurance(
                agent_id,
                capability
            )

        print("\n=== TYPED DEPENDENCIES ===")

        self.tsdm.print_dependencies()
        
        
        
        
    def get_evidence_status(self, agent_id, capability):
    return self.eas.status(
        agent_id,
        capability,
    )


    def get_contradiction_score(self, agent_id, capability):
    return self.eas.contradiction_score(
        agent_id,
        capability,
    )


    def add_historical_evidence(
        self,
        agent_id,
        capability,
        outcome,
        support,
        timestamp,
    ):
    self.eas.add_evidence(
        agent_id,
        capability,
        outcome,
        support,
        timestamp=timestamp,
        source="historical",
    )