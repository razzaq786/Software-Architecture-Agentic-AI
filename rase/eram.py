from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


def now_utc():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentState:
    agent_id: str
    capability: str
    responsibility: str
    status: str = "available"
    last_update: str = ""


@dataclass
class Dependency:
    source: str
    target: str
    relation_type: str
    assurance: float = 1.0


class ERAM:
    def __init__(self):
        self.agents: Dict[str, AgentState] = {}
        self.dependencies: List[Dependency] = []

    def register_agent(
        self,
        agent_id: str,
        capability: str,
        responsibility: str
    ):
        self.agents[agent_id] = AgentState(
            agent_id=agent_id,
            capability=capability,
            responsibility=responsibility,
            last_update=now_utc()
        )

    def update_agent_status(self, agent_id: str, status: str):
        if agent_id not in self.agents:
            raise ValueError(f"Unknown agent: {agent_id}")

        self.agents[agent_id].status = status
        self.agents[agent_id].last_update = now_utc()

    def add_dependency(
        self,
        source: str,
        target: str,
        relation_type: str,
        assurance: float = 1.0
    ):
        dependency = Dependency(
            source=source,
            target=target,
            relation_type=relation_type,
            assurance=assurance
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

    def get_state(self):
        return {
            "agents": {
                agent_id: {
                    "capability": state.capability,
                    "responsibility": state.responsibility,
                    "status": state.status,
                    "last_update": state.last_update
                }
                for agent_id, state in self.agents.items()
            },
            "dependencies": [
                {
                    "source": dependency.source,
                    "target": dependency.target,
                    "relation_type": dependency.relation_type,
                    "assurance": dependency.assurance
                }
                for dependency in self.dependencies
            ]
        }

    def print_state(self):
        print("\n=== ERAM STATE ===")

        print("\nAgents:")
        for agent in self.agents.values():
            print(
                f"  {agent.agent_id}: "
                f"capability={agent.capability}, "
                f"responsibility={agent.responsibility}, "
                f"status={agent.status}"
            )

        print("\nDependencies:")
        for dependency in self.dependencies:
            print(
                f"  {dependency.source} "
                f"--[{dependency.relation_type}]--> "
                f"{dependency.target} "
                f"(assurance={dependency.assurance:.2f})"
            )