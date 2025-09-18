from __future__ import annotations

from typing import Literal

Level = Literal["minimal", "normal", "verbose"]


class DisclosureConfig:
    def __init__(self, level: Level = "normal") -> None:
        self.level = level

    def should_show(self, level: Level, stage: int) -> bool:
        if self.level == "verbose":
            return True
        if self.level == "normal":
            return level in ("minimal", "normal")
        # minimal mode
        return level == "minimal" and stage in ("summary", 0, 1)

