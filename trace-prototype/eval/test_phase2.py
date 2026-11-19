from core.store import PolicyStore
from eval.scorer import run_benchmark

def main():
    store = PolicyStore()
    store.clear_all()

    print("--- Committing 2 manual patches to PolicyStore ---")
    p1 = store.commit_patch(
        content="When calculating revenue from the orders table, always use SUM(net_amount) and filter WHERE status = 'completed' AND is_deleted = 0.",
        patch_type="instruction",
        scope="global",
        reason="Manual Phase 2 test: revenue rule",
    )
    p2 = store.commit_patch(
        content="When querying customers or orders, always exclude soft-deleted records by adding is_deleted = 0.",
        patch_type="instruction",
        scope="global",
        reason="Manual Phase 2 test: soft-delete rule",
    )
    print(f"Committed: {p1.commit_id} and {p2.commit_id}\n")

    active_rules = [p.content for p in store.get_active_policies()]
    print("--- Re-running Benchmark WITH Versioned Policies ---")
    run_benchmark(policies=active_rules)

    print(f"\n--- Testing Rollback of {p1.commit_id} ---")
    store.rollback_commit(p1.commit_id)
    remaining = [p.content for p in store.get_active_policies()]
    print(f"Active policies after rollback: {len(remaining)}")
    for r in remaining:
        print(f" - {r}")

if __name__ == "__main__":
    main()