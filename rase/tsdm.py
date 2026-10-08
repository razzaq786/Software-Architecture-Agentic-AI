from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TypedDependency:
    source: str
    target: str
    relation_type: str
    propagation_weight: float = 1.0


class TSDM:
    """
    Typed Semantic Dependency Model.

    Maintains semantic dependencies between agents and propagates
    architectural impact according to dependency type and assurance.
    """

    PROPAGATING_RELATIONS = {
        "produces-event",
        "produces-result",
        "supports-responsibility",
        "provides-capability",
        "affects-goal",
    }

    def __init__(self):
        self.dependencies: List[TypedDependency] = []

    def add_dependency(
        self,
        source: str,
        target: str,
        relation_type: str,
        propagation_weight: float = 1.0
    ):
        dependency = TypedDependency(
            source=source,
            target=target,
            relation_type=relation_type,
            propagation_weight=propagation_weight
        )

        # Avoid duplicate active dependencies.
        if not any(
            d.source == source
            and d.target == target
            and d.relation_type == relation_type
            for d in self.dependencies
        ):
            self.dependencies.append(dependency)

    def remove_dependency(
        self,
        source: str,
        target: str,
        relation_type: str
    ):
        self.dependencies = [
            dependency
            for dependency in self.dependencies
            if not (
                dependency.source == source
                and dependency.target == target
                and dependency.relation_type == relation_type
            )
        ]

    def get_outgoing(self, source: str):
        return [
            dependency
            for dependency in self.dependencies
            if dependency.source == source
        ]

    def propagate_impact(
        self,
        changed_agent: str,
        assurance: Dict[str, float],
        threshold: float = 0.1
    ):
        impact = {
            changed_agent: 1.0
        }

        queue = [changed_agent]

        while queue:
            current = queue.pop(0)
            current_impact = impact[current]

            for dependency in self.get_outgoing(current):

                if dependency.relation_type not in self.PROPAGATING_RELATIONS:
                    continue

                target = dependency.target

                target_assurance = assurance.get(target, 1.0)

                propagated_impact = (
                    current_impact
                    * dependency.propagation_weight
                    * target_assurance
                )

                if propagated_impact < threshold:
                    continue

                if (
                    target not in impact
                    or propagated_impact > impact[target]
                ):
                    impact[target] = propagated_impact

                    if target not in queue:
                        queue.append(target)

        return impact

    def print_dependencies(self):
        print("\n=== TSDM DEPENDENCIES ===")

        for dependency in self.dependencies:
            print(
                f"{dependency.source} "
                f"--[{dependency.relation_type}]--> "
                f"{dependency.target} "
                f"(weight={dependency.propagation_weight:.2f})"
            )