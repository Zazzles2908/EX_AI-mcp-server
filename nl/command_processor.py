from __future__ import annotations

from typing import Dict


def parse_command(text: str) -> Dict[str, object]:
    """Very small keyword-based parser: "run tool=NAME expert=true steps=2" -> dict.
    Unknown tokens ignored. Values are not type-strict.
    """
    parts = (text or "").split()
    out: Dict[str, object] = {"action": parts[0] if parts else ""}
    for tok in parts[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            # normalize booleans/ints when obvious
            if v.lower() in ("true", "false"):
                out[k] = v.lower() == "true"
            else:
                try:
                    out[k] = int(v)
                except Exception:
                    out[k] = v
    return out

