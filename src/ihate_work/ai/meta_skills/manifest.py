"""Provenance records for installed skills.

A manifest lives next to the installed skills (in dest.skills_dir) and maps
skill dir name -> where the snapshot/link came from, so a later run can
detect drift (source rev changed since install) and offer a re-install.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

MANIFEST_NAME = ".meta-skills.json"


def _manifest_path(skills_dir: Path) -> Path:
    return skills_dir / MANIFEST_NAME


def load(skills_dir: Path) -> dict[str, dict]:
    p = _manifest_path(skills_dir)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        # transient, rebuildable metadata must never block anything:
        # quarantine and continue empty
        bad = p.with_name(p.name + ".bad")
        p.rename(bad)
        print(
            f"warning: corrupt manifest quarantined as {bad}; treating as empty",
            file=sys.stderr,
        )
        return {}


def record(
    skills_dir: Path,
    *,
    skill_name: str,
    skill_id: str,
    method: str,
    source_rev: str | None,
) -> None:
    entries = load(skills_dir)
    entries[skill_name] = {
        "skill": skill_id,
        "method": method,
        "source_rev": source_rev,
        "installed_at": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"
        ),
    }
    _manifest_path(skills_dir).write_text(json.dumps(entries, indent=2) + "\n")


def forget(skills_dir: Path, skill_name: str) -> None:
    entries = load(skills_dir)
    if entries.pop(skill_name, None) is not None:
        _manifest_path(skills_dir).write_text(json.dumps(entries, indent=2) + "\n")
