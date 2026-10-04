from __future__ import annotations


def logical_validity_score(checks_passed: int, checks_total: int) -> float:
    if checks_total <= 0:
        return 0.0
    return max(0.0, min(1.0, checks_passed / checks_total))