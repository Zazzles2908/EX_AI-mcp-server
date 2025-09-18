from __future__ import annotations

from typing import Dict


def choose_model_data_driven(provider_metrics: Dict[str, Dict[str, float]]) -> str:
    """Pick provider:model based on success_rate then latency.
    provider_metrics example:
    {
      "zai:glm-4.5-flash": {"success_rate": 0.995, "p95_ms": 800},
      "moonshot:kimi-k2-0711-preview": {"success_rate": 0.990, "p95_ms": 1200}
    }
    """
    if not provider_metrics:
        return "zai:glm-4.5-flash"
    # Sort by success_rate desc, then p95_ms asc
    items = sorted(
        provider_metrics.items(),
        key=lambda kv: (-kv[1].get("success_rate", 0.0), kv[1].get("p95_ms", 999999)),
    )
    return items[0][0]

