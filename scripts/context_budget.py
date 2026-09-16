#!/usr/bin/env python3
"""根据模型上下文窗口计算 source-analyzer 的 LLM 请求预算。

这个模块不调用 provider，只生成运行时适配层可消费的请求参数。
优先级：显式参数 > SOURCE_ANALYZER_CONTEXT_WINDOW > 已知模型映射 > 保守默认值。
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Optional


DEFAULT_CONTEXT_WINDOW = 256_000
INPUT_RATIO = 0.75
MIN_OUTPUT_TOKENS = 32_000
MAX_OUTPUT_TOKENS = 64_000
MODEL_CONTEXT_WINDOWS = {
    # 仅作为没有运行时元数据时的保守提示；provider 返回值优先。
    "claude-3-5-sonnet": 200_000,
    "claude-3-7-sonnet": 200_000,
    "claude-4": 200_000,
    "gemini-1.5": 1_000_000,
    "gemini-2": 1_000_000,
    "gpt-4.1": 1_000_000,
    "gpt-5": 1_000_000,
}


def _positive_int(value: object, name: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        parsed = int(str(value).replace(",", "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def detect_context_window(model: str, explicit: Optional[object] = None) -> tuple[int, str]:
    value = _positive_int(explicit, "context_window")
    if value:
        return value, "explicit"

    value = _positive_int(os.environ.get("SOURCE_ANALYZER_CONTEXT_WINDOW"), "SOURCE_ANALYZER_CONTEXT_WINDOW")
    if value:
        return value, "environment"

    normalized = (model or "").lower()
    for pattern, window in MODEL_CONTEXT_WINDOWS.items():
        if pattern in normalized:
            return window, f"model-map:{pattern}"
    return DEFAULT_CONTEXT_WINDOW, "default"


def calculate_budget(
    model: str,
    context_window: Optional[object] = None,
    input_ratio: float = INPUT_RATIO,
) -> dict:
    if not 0 < input_ratio < 1:
        raise ValueError("input_ratio must be between 0 and 1")
    total, source = detect_context_window(model, context_window)
    output_reserve = min(MAX_OUTPUT_TOKENS, max(MIN_OUTPUT_TOKENS, total // 8))
    input_budget = min(int(total * input_ratio), total - output_reserve)
    return {
        "model": model or "unknown",
        "context_window": total,
        "context_window_source": source,
        "input_ratio": input_ratio,
        "max_input_tokens": input_budget,
        "max_output_tokens": output_reserve,
        "request_context_tokens": input_budget + output_reserve,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="计算 source-analyzer 的模型上下文预算")
    parser.add_argument("--model", default=os.environ.get("OPENCLAW_MODEL", "unknown"))
    parser.add_argument("--context-window", type=int, default=None)
    parser.add_argument("--input-ratio", type=float, default=INPUT_RATIO)
    args = parser.parse_args()
    print(json.dumps(calculate_budget(args.model, args.context_window, args.input_ratio), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
