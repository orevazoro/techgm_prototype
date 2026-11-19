import json
from pathlib import Path
from core.agent import run_agent, execute_sql_readonly

TASKS_PATH = Path("eval/tasks.json")

def normalize_result(rows):
    if rows is None:
        return None
    # Round floats to avoid minor precision mismatches
    return [
        tuple(round(v, 2) if isinstance(v, float) else v for v in row)
        for row in rows
    ]

def score_task(task: dict, policies: list[str] | None = None) -> dict:
    gt_rows, gt_err = execute_sql_readonly(task["ground_truth_sql"])
    if gt_err:
        raise ValueError(f"Ground truth SQL failed for {task['task_id']}: {gt_err}")

    trace = run_agent(task["question"], policies=policies)
    passed = (
        trace.error is None
        and normalize_result(trace.result) == normalize_result(gt_rows)
    )

    return {
        "task_id": task["task_id"],
        "category": task["category"],
        "passed": passed,
        "expected": gt_rows,
        "actual": trace.result,
        "sql": trace.sql,
        "error": trace.error,
        "latency_ms": trace.latency_ms,
    }

def run_benchmark(policies: list[str] | None = None):
    tasks = json.loads(TASKS_PATH.read_text())
    results = []
    passed_count = 0

    for task in tasks:
        res = score_task(task, policies=policies)
        results.append(res)
        status = "PASS" if res["passed"] else "FAIL"
        if res["passed"]:
            passed_count += 1
        print(f"[{status}] {res['task_id']} ({res['category']}) | {res['latency_ms']}ms")
        if not res["passed"]:
            print(f"   Expected: {res['expected']} | Got: {res['actual']}")
            print(f"   Agent SQL: {res['sql']}")

    accuracy = (passed_count / len(tasks)) * 100
    print(f"\nBaseline Score: {passed_count}/{len(tasks)} ({accuracy:.1f}%)")
    return results

if __name__ == "__main__":
    run_benchmark()