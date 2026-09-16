#!/usr/bin/env python3
"""context_budget.py 的最小回归测试。"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import context_budget


def main():
    assert context_budget.calculate_budget("unknown")["context_window"] == 256_000
    assert context_budget.calculate_budget("gpt-5")["context_window"] == 1_000_000
    assert context_budget.calculate_budget("x", 1_000_000)["context_window"] == 1_000_000
    assert context_budget.calculate_budget("x", 1_000_000)["max_input_tokens"] == 750_000
    old = os.environ.get("SOURCE_ANALYZER_CONTEXT_WINDOW")
    os.environ["SOURCE_ANALYZER_CONTEXT_WINDOW"] = "256000"
    try:
        assert context_budget.calculate_budget("gpt-5")["context_window_source"] == "environment"
    finally:
        if old is None:
            os.environ.pop("SOURCE_ANALYZER_CONTEXT_WINDOW", None)
        else:
            os.environ["SOURCE_ANALYZER_CONTEXT_WINDOW"] = old
    print("context budget tests passed")


if __name__ == "__main__":
    main()
