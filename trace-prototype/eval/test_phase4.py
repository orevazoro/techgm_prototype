import json
from pathlib import Path
from core.collector import FeedbackCollector
from core.evaluator import evaluate_feedback
from core.hypothesis import CandidatePatch, generate_hypothesis
from core.store import PolicyStore
from core.validator import validate_patch

TASKS = json.loads(Path("eval/tasks.json").read_text())
TASK_MAP = {t["task_id"]: t for t in TASKS}


def main():
    store = PolicyStore()
    store.clear_all()
    collector = FeedbackCollector()

    regression_suite = [TASK_MAP["t1"], TASK_MAP["t2"]]

    print("=== TEST 1: Full TRACE Loop on t3 (Revenue Rule) ===")
    ev = collector.record(
        task_id="t3",
        user_id="user_1",
        question=TASK_MAP["t3"]["question"],
        trace_json='{"sql": "SELECT SUM(net_amount) FROM orders"}',
        output="SELECT SUM(net_amount) FROM orders",
        signal_type="correction",
        value="When calculating revenue from orders, only include rows where status = 'completed' and is_deleted = 0.",
    )

    trust = evaluate_feedback(ev)
    print(f"[2] Trust Evaluator : {trust.decision.upper()} (cred={trust.credibility}, rel={trust.relevance}, risk={trust.risk})")

    if trust.decision == "accept":
        current_policies = [p.content for p in store.get_active_policies()]
        patch = generate_hypothesis(ev, existing_policies=current_policies)
        print(f"[3] Hypothesis Patch: [{patch.patch_type} | {patch.scope}] {patch.content}")

        val = validate_patch(patch, TASK_MAP["t3"], regression_suite, current_policies)
        print(f"[4] Validator       : approved={val.approved} | net_score={val.net_score} | {val.reason}")

        if val.approved:
            entry = store.commit_patch(
                content=patch.content,
                patch_type=patch.patch_type,
                scope=patch.scope,
                reason=patch.target_failure,
            )
            print(f"[5] Committed       : {entry.commit_id}\n")

    print("=== TEST 2: Regression Guardrail (Over-broad Patch) ===")
    bad_patch = CandidatePatch(
        patch_type="instruction",
        content="Always add WHERE is_deleted = 0 to every SQL query on all tables.",
        scope="global",
        target_failure="Exclude soft-deleted customers",
    )
    current_policies = [p.content for p in store.get_active_policies()]
    val_bad = validate_patch(bad_patch, TASK_MAP["t5"], regression_suite, current_policies)
    print(f"[4] Validator       : approved={val_bad.approved} | regressions={val_bad.regressions} | {val_bad.reason}")


if __name__ == "__main__":
    main()