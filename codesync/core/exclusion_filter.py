from __future__ import annotations

try:
    import pathspec
    _PATHSPEC_AVAILABLE = True
except ImportError:
    _PATHSPEC_AVAILABLE = False


class ExclusionFilter:
    """Matches file paths against .gitignore-style exclusion patterns."""

    def __init__(self, patterns: list[str]):
        self._patterns = patterns
        if _PATHSPEC_AVAILABLE and patterns:
            self._spec = pathspec.PathSpec.from_lines("gitignore", patterns)
        else:
            self._spec = None

    def is_excluded(self, relative_path: str) -> bool:
        """Return True if the relative path matches any exclusion pattern."""
        if not self._patterns:
            return False
        if self._spec is not None:
            # Normalise to forward slashes for pathspec
            return self._spec.match_file(relative_path.replace("\\", "/"))
        # Fallback: simple suffix matching when pathspec is unavailable
        rel = relative_path.replace("\\", "/")
        for pat in self._patterns:
            pat = pat.rstrip("/")
            if pat.startswith("*."):
                if rel.endswith(pat[1:]):
                    return True
            elif pat in rel:
                return True
        return False
