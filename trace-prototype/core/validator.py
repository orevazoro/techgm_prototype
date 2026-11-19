from typing import List
from pydantic import BaseModel
from core.hypothesis import CandidatePatch
from eval.scorer import score_task
from pathlib import Path
from core.agent import execute_sql_readonly, run_agent

class ValidationResult(BaseModel):
    approved: bool
    target_before: bool
    target_after: bool
    target_gain: float
    regressions: List[str]
    net_score: float
    reason: str


def validate_patch(
    patch: CandidatePatch,
    target_task: dict,
    regression_tasks: List[dict],
    current_policies: List[str],
    regression_penalty: float = 2.0,
) -> ValidationResult:
    candidate_policies = current_policies + [patch.content]

    # 1. Paired Replay on the failing target task
    before = score_task(target_task, policies=current_policies)
    after = score_task(target_task, policies=candidate_policies)

    target_before = before["passed"]
    target_after = after["passed"]
    target_gain = (1.0 if target_after else 0.0) - (1.0 if target_before else 0.0)

    # 2. Cross-Task Regression Check
    regressions: List[str] = []
    for task in regression_tasks:
        if task["task_id"] == target_task["task_id"]:
            continue
        reg_before = score_task(task, policies=current_policies)
        if reg_before["passed"]:
            reg_after = score_task(task, policies=candidate_policies)
            if not reg_after["passed"]:
                regressions.append(task["task_id"])

    net_score = target_gain - (regression_penalty * len(regressions))

    if target_gain <= 0:
        return ValidationResult(
            approved=False,
            target_before=target_before,
            target_after=target_after,
            target_gain=target_gain,
            regressions=regressions,
            net_score=net_score,
            reason="Rejected: Patch did not improve the target task in paired replay.",
        )

    if regressions:
        return ValidationResult(
            approved=False,
            target_before=target_before,
            target_after=target_after,
            target_gain=target_gain,
            regressions=regressions,
            net_score=net_score,
            reason=f"Rejected: Caused cross-task regressions on {regressions}.",
        )

    return ValidationResult(
        approved=True,
        target_before=target_before,
        target_after=target_after,
        target_gain=target_gain,
        regressions=[],
        net_score=net_score,
        reason="Approved: Improved target task with zero regressions.",
    )
class _CustomValidationResult:
    def __init__(self, approved: bool, net_score: float, reason: str, regressions=None):
        self.approved = approved
        self.net_score = net_score
        self.reason = reason
        self.regressions = regressions or []


def validate_custom_db_patch(
    patch,
    question: str,
    db_path: str | Path,
    curr_policies: list[str],
):
    candidate_policies = curr_policies + [patch.content]
    trace = run_agent(question, policies=candidate_policies, db_path=db_path)
    if trace.error:
        return _CustomValidationResult(
            approved=False,
            net_score=-1.0,
            reason=f"Patched query failed execution: {trace.error}",
        )

    _, recheck_err = execute_sql_readonly(trace.sql, db_path=db_path)
    if recheck_err:
        return _CustomValidationResult(
            approved=False,
            net_score=-1.0,
            reason=f"Read-only recheck failed: {recheck_err}",
        )

    return _CustomValidationResult(
        approved=True,
        net_score=1.0,
        reason="Patched query executed cleanly on custom SQLite database.",
    )