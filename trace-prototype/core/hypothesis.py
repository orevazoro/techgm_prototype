from typing import Literal
from pydantic import BaseModel
from core.agent import get_db_schema
from core.collector import FeedbackEvent
from core.llm import call_llm_structured


class CandidatePatch(BaseModel):
    patch_type: Literal["memory", "instruction", "tool_rule", "workflow"]
    content: str
    scope: str          # "global" or "user:<user_id>"
    target_failure: str # Brief summary of the mistake this fixes


def generate_hypothesis(
    event: FeedbackEvent,
    existing_policies: list[str] | None = None,
) -> CandidatePatch:
    schema = get_db_schema()
    existing_block = (
        "\n".join(f"- {p}" for p in existing_policies)
        if existing_policies
        else "None"
    )

    system_prompt = (
        "You are the Hypothesis Engine for a Text-to-SQL AI agent. "
        "Turn the user feedback into ONE complete 1-sentence instruction for the target table.\n"
        "STRICT RULES:\n"
        "- Write a complete sentence (for example: 'When querying orders, filter by status = \\'completed\\' and is_deleted = 0.').\n"
        "- NO standalone SQL clauses or SELECT/WHERE fragments by themselves.\n"
        "- Name ONLY the target table mentioned in the feedback and its exact column filters.\n"
        "- Never add filters to other tables.\n"
        "- Use scope='global' for universal rules, or scope='user:<user_id>' for personal preferences.\n"
        "Return strict JSON matching the schema."
    )
    user_prompt = (
        f"Database Schema:\n{schema}\n\n"
        f"Existing Policies:\n{existing_block}\n\n"
        f"User ID: {event.user_id}\n"
        f"Target Task ID: {event.task_id}\n"
        f"Question: {event.question}\n"
        f"Failed SQL: {event.output}\n"
        f"User Feedback: {event.value}\n"
    )

    return call_llm_structured(system_prompt, user_prompt, CandidatePatch)