"""Domain errors.

Every *expected* failure mode raises MetaSkillsError (or a subclass); the
CLI boundary converts exactly these into one-line messages. Anything else
escaping is a bug and is allowed to traceback so it gets seen and fixed.
"""

from __future__ import annotations


class MetaSkillsError(Exception):
    pass


class TargetExists(MetaSkillsError, FileExistsError):
    """The install target is already present and --force was not given.

    The CLI treats this as a per-skill *skip*, not a run failure.
    """
