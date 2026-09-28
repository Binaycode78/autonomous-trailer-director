from src.utils.cost_tracker import CostTracker
from src.verification.source_checker import RiskFlag

def check_budget(cost_tracker: CostTracker) -> tuple[list[RiskFlag], bool]:
    flags = []
    summary = cost_tracker.get_summary()
    total = summary["total_cost"]
    limit = summary["budget_limit"]
    fallback = False
    
    if total > limit:
        flags.append(RiskFlag("BudgetChecker", "HARD FAIL", f"Over budget: {total} > {limit}"))
        fallback = True
    elif limit > 0 and total >= limit * 0.8:
        flags.append(RiskFlag("BudgetChecker", "SOFT FAIL", f"Within 80% of budget: {total} / {limit}"))
        
    return flags, fallback
