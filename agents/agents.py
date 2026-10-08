from dataclasses import dataclass
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentResult:
    agent_id: str
    task: str
    success: bool
    output: dict
    timestamp: str


class VisitAnalysisAgent:

    def __init__(self):
        self.agent_id = "A1"
        self.capability = "VisitAnalysis"
        self.responsibility = "AnalyzeVisit"

    def analyze(self, visit_request):

        output = {
            "pet_id": visit_request["pet_id"],
            "date": visit_request["date"],
            "event": "VisitBooked"
        }

        return AgentResult(
            agent_id=self.agent_id,
            task="AnalyzeVisitRequest",
            success=True,
            output=output,
            timestamp=now_utc()
        )


class VetAssignmentAgent:

    def __init__(
        self,
        agent_id="A2",
        available=True,
        degraded=False
    ):
        self.agent_id = agent_id
        self.capability = "VetAssignment"
        self.responsibility = "AssignVet"
        self.available = available
        self.degraded = degraded

    def assign(self, visit_event):

        if not self.available:

            return AgentResult(
                agent_id=self.agent_id,
                task="AssignVeterinarian",
                success=False,
                output={
                    "error": "agent_unavailable"
                },
                timestamp=now_utc()
            )

        if self.degraded:

            return AgentResult(
                agent_id=self.agent_id,
                task="AssignVeterinarian",
                success=False,
                output={
                    "error": "degraded_assignment",
                    "pet_id": visit_event["pet_id"],
                    "date": visit_event["date"]
                },
                timestamp=now_utc()
            )

        output = {
            "pet_id": visit_event["pet_id"],
            "date": visit_event["date"],
            "vet_id": 1,
            "assignment": "successful"
        }

        return AgentResult(
            agent_id=self.agent_id,
            task="AssignVeterinarian",
            success=True,
            output=output,
            timestamp=now_utc()
        )


class VerificationAgent:

    def __init__(self):
        self.agent_id = "A3"
        self.capability = "AssignmentVerification"
        self.responsibility = "VerifyAssignment"

    def verify(self, assignment):

        required_fields = [
            "pet_id",
            "date",
            "vet_id",
            "assignment"
        ]

        valid_fields = all(
            field in assignment
            for field in required_fields
        )

        successful_assignment = (
            assignment.get("assignment") == "successful"
        )

        verified = (
            valid_fields
            and successful_assignment
            and assignment.get("vet_id") is not None
        )

        return AgentResult(
            agent_id=self.agent_id,
            task="VerifyAssignment",
            success=verified,
            output={
                "verified": verified,
                "checked_fields": required_fields
            },
            timestamp=now_utc()
        )