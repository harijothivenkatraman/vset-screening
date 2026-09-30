from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.entities.action_item import ActionItem


def map_action_items_from_raw(raw_data: dict[str, Any], report_id: UUID) -> list[ActionItem]:
    content = raw_data.get("canonical", {}).get("content", {})
    now = datetime.now(timezone.utc)
    action_items: list[ActionItem] = []
    position = 0

    # 1. Map SECTION_REQUEST items from canonical.content.actions
    raw_actions = content.get("actions", [])
    for action in raw_actions:
        if action.get("kind") == "SECTION_REQUEST":
            action_items.append(
                ActionItem(
                    id=uuid4(),
                    report_id=report_id,
                    action_id=action.get("id", f"ACT-{position}"),
                    kind="SECTION_REQUEST",
                    where=action.get("where"),
                    domain=action.get("domain"),
                    topic=None,
                    group_name=None,
                    text=action.get("text", ""),
                    why=action.get("why"),
                    key=action.get("key"),
                    semantic_key=action.get("semantic_key"),
                    priority_level=None,
                    position=position,
                    created_at=now,
                )
            )
            position += 1

    # 2. Map DD_QUESTION items from canonical.content.action_requirements.topics
    action_reqs = content.get("action_requirements", {})
    topics = action_reqs.get("topics", [])
    for topic_obj in topics:
        topic_name = topic_obj.get("topic", "")
        for item in topic_obj.get("items", []):
            action_items.append(
                ActionItem(
                    id=uuid4(),
                    report_id=report_id,
                    action_id=item.get("id", f"Q-{position}"),
                    kind="DD_QUESTION",
                    where="A",
                    domain=topic_name,
                    topic=topic_name,
                    group_name=None,
                    text=item.get("text", ""),
                    why=item.get("why"),
                    key=item.get("key"),
                    semantic_key=item.get("semantic_key"),
                    priority_level=None,
                    position=position,
                    created_at=now,
                )
            )
            position += 1

    # 3. Map DD_DOCUMENT items from canonical.content.action_requirements.documents
    documents = action_reqs.get("documents", [])
    for doc_group in documents:
        group_name = doc_group.get("group", "")
        priority_docs = doc_group.get("priority", [])
        priority_ids = doc_group.get("priority_ids", [])
        for idx, doc_text in enumerate(priority_docs):
            doc_id = priority_ids[idx] if idx < len(priority_ids) else f"DOC-{position}"
            action_items.append(
                ActionItem(
                    id=uuid4(),
                    report_id=report_id,
                    action_id=doc_id,
                    kind="DD_DOCUMENT",
                    where="B",
                    domain=group_name,
                    topic=None,
                    group_name=group_name,
                    text=doc_text,
                    why=None,
                    key=None,
                    semantic_key=None,
                    priority_level="priority",
                    position=position,
                    created_at=now,
                )
            )
            position += 1

        secondary_docs = doc_group.get("secondary", [])
        secondary_ids = doc_group.get("secondary_ids", [])
        for idx, doc_text in enumerate(secondary_docs):
            doc_id = secondary_ids[idx] if idx < len(secondary_ids) else f"DOC-{position}"
            action_items.append(
                ActionItem(
                    id=uuid4(),
                    report_id=report_id,
                    action_id=doc_id,
                    kind="DD_DOCUMENT",
                    where="B",
                    domain=group_name,
                    topic=None,
                    group_name=group_name,
                    text=doc_text,
                    why=None,
                    key=None,
                    semantic_key=None,
                    priority_level="secondary",
                    position=position,
                    created_at=now,
                )
            )
            position += 1

    return action_items
