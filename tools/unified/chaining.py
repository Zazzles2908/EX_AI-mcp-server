from __future__ import annotations

from typing import Callable, Dict, Any, List


class ChainRunner:
    """Run a list of callables(context)->dict, threading context through."""

    def __init__(self, steps: List[Callable[[Dict[str, Any]], Dict[str, Any]]]):
        self.steps = steps

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(context)
        for step in self.steps:
            out = step(state)
            if out:
                state.update(out)
        return state

