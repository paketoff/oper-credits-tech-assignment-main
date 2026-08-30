"""Serving the built Angular bundle and the routes Angular owns (DEP-013, DEP-014).

One container serves both the API and the frontend (DEP-001), so this module
answers every request that no `/api` route and neither probe claimed. Two
outcomes and no third:

* **The path names a file that was built** — `main-<hash>.js`, `styles-<hash>.css`,
  `favicon.svg` — so it is returned as itself, with the media type its suffix
  implies. This is the case the previous implementation did not have, and its
  absence broke the production container completely: Angular's application
  builder emits hashed bundles at the *root* of `dist/.../browser`, not under
  `assets/`, so the mount that existed never matched anything and every bundle
  fell through to the shell below. The browser then refused `index.html` as a
  module script on a MIME check and the application never booted, while every
  response was still a 200.
* **Anything else** is a client-side route, and gets the shell. A refresh on a
  deep link must not 404 (DEP-014), and the server cannot know Angular's route
  table.

`/api/*` is excluded explicitly: the catch-all that calls this is registered
last and matches literally everything, so an undefined API path would otherwise
be answered with the shell and a 200 instead of a clean 404.
"""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

_API_PREFIX = "api/"
_INDEX = "index.html"


def _built_file(static_dir: Path, path: str) -> Path | None:
    """The built file this path names, or None if it names none.

    The candidate is resolved and checked against the static root before it is
    used. Nothing here is user data in the ordinary sense — the paths come from
    a bundle we built — but this function takes an arbitrary URL path, and the
    cost of being wrong about that is reading any file the process can reach.
    """
    if not path:
        return None
    candidate = (static_dir / path).resolve()
    if not candidate.is_relative_to(static_dir.resolve()):
        return None
    return candidate if candidate.is_file() else None


def response_for(static_dir: Path, path: str) -> FileResponse:
    """Answer one non-API request: the file if it was built, else the shell.

    Args:
        static_dir: Where the Angular build was copied to.
        path: The request path, without its leading slash.

    Returns:
        The built file, or `index.html` for a client-side route.

    Raises:
        HTTPException: 404 for an `/api` path. Not a `DomainError`: no domain
            was consulted, and there is no registry code for "this API route
            does not exist" (CQ-063).
    """
    if path.startswith(_API_PREFIX):
        raise HTTPException(status_code=404)
    built = _built_file(static_dir, path)
    return FileResponse(built if built is not None else static_dir / _INDEX)
