from typing import Any

from app.application.ports.action_item_repository import ActionItemRepository
from app.application.ports.company_repository import CompanyRepository
from app.application.ports.report_repository import ReportRepository


class ActionsData:
    def __init__(
        self,
        concerns: dict[str, Any],
        presentation: dict[str, Any],
        questions: list[dict[str, Any]],
        documents: list[dict[str, Any]],
    ) -> None:
        self.concerns = concerns
        self.presentation = presentation
        self.questions = questions
        self.documents = documents

    def to_dict(self) -> dict[str, Any]:
        return {
            "concerns": self.concerns,
            "presentation": self.presentation,
            "questions": self.questions,
            "documents": self.documents,
        }


class GetActionsService:
    def __init__(
        self,
        company_repo: CompanyRepository,
        report_repo: ReportRepository,
        action_item_repo: ActionItemRepository,
    ) -> None:
        self._company_repo = company_repo
        self._report_repo = report_repo
        self._action_item_repo = action_item_repo

    async def execute(self, slug: str) -> ActionsData | None:
        company = await self._company_repo.find_by_slug(slug)
        if company is None:
            return None

        report = await self._report_repo.find_by_company_id(company.id)
        if report is None:
            return None

        # Concerns & Conflicts logic
        raw_cc = report.concerns_conflicts or {}
        concerns_list = raw_cc.get("concerns", [])
        conflicts_list = raw_cc.get("conflicts", [])
        message = "No public concern or source conflict is recorded in this baseline."
        if concerns_list or conflicts_list:
            message = ""

        concerns_obj = {
            "concerns": concerns_list,
            "conflicts": conflicts_list,
            "message": message,
        }

        # Presentation metadata
        pres = report.presentation or {}
        presentation_obj = {
            "actionIntro": pres.get(
                "action_intro",
                "Part A lists the questions an investor is likely to raise after reviewing the public record; Part B lists the documents and data that evidence them.",
            ),
            "partATitle": pres.get("action_part_a_title", "A. Questions to prepare for"),
            "partBTitle": pres.get("action_part_b_title", "B. Supporting documents & data to prepare"),
            "actionSectionTitle": pres.get("action_section_title", "Investor questions & information to prepare"),
        }

        # Tab 8 Part A: Questions grouped by topic
        actions = await self._action_item_repo.find_by_report_id(report.id)

        # Questions
        questions_by_topic: dict[str, list[dict[str, Any]]] = {}
        for a in actions:
            if a.kind == "DD_QUESTION":
                topic_name = a.topic or a.domain or "General"
                if topic_name not in questions_by_topic:
                    questions_by_topic[topic_name] = []
                questions_by_topic[topic_name].append(
                    {
                        "id": a.action_id,
                        "text": a.text,
                        "why": a.why,
                    }
                )

        questions = [
            {"topic": topic, "items": items}
            for topic, items in questions_by_topic.items()
        ]

        # Documents grouped by group_name
        documents_by_group: dict[str, dict[str, list[str]]] = {}
        for a in actions:
            if a.kind == "DD_DOCUMENT":
                group = a.group_name or a.domain or "General"
                if group not in documents_by_group:
                    documents_by_group[group] = {"priority": [], "secondary": []}
                if a.priority_level == "priority":
                    documents_by_group[group]["priority"].append(a.text)
                else:
                    documents_by_group[group]["secondary"].append(a.text)

        documents = [
            {
                "group": group,
                "priority": docs["priority"],
                "secondary": docs["secondary"],
            }
            for group, docs in documents_by_group.items()
        ]

        return ActionsData(
            concerns=concerns_obj,
            presentation=presentation_obj,
            questions=questions,
            documents=documents,
        )
