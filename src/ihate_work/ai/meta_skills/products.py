"""The per-product skill directory table.

Surveyed in docs/skill-dirs.md — keep the two in sync. Nothing outside this
module may hardcode a product convention like ".claude".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Product:
    key: str  # CLI value for --product
    name: str  # display name
    project_skills: str  # skills dir relative to a REPO/DIR dest root
    global_skills: Path  # user-level skills dir (HOME dest), unexpanded

    @property
    def marker(self) -> str:
        """The config dir whose presence marks a dest as using this product."""
        return self.project_skills.split("/", 1)[0]


PRODUCTS = [
    Product("claude", "Claude Code", ".claude/skills", Path("~/.claude/skills")),
    Product("codex", "Codex CLI", ".codex/skills", Path("~/.codex/skills")),
    Product("pi", "pi", ".pi/skills", Path("~/.pi/agent/skills")),
    Product("omp", "oh-my-pi", ".omp/skills", Path("~/.omp/agent/skills")),
    Product("agents", "neutral .agents", ".agents/skills", Path("~/.agents/skills")),
]


def by_key(key: str) -> Product:
    return next(p for p in PRODUCTS if p.key == key)
