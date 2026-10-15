"""RFC 7807 problem+json with a machine-readable ``code`` (build spec §9).

Every error the API returns has the same shape, so the frontend can branch on ``code``
rather than parsing prose.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CONTENT_TYPE = "application/problem+json"


class ProblemError(Exception):
    """Raise this anywhere in the app; the handler below renders it."""

    def __init__(
        self,
        *,
        code: str,
        title: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str | None = None,
        **extra: Any,
    ) -> None:
        super().__init__(title)
        self.code = code
        self.title = title
        self.status_code = status_code
        self.detail = detail
        self.extra = extra

    def body(self, instance: str) -> dict[str, Any]:
        out: dict[str, Any] = {
            "type": f"https://sora-copilot.eu/problems/{self.code}",
            "code": self.code,
            "title": self.title,
            "status": self.status_code,
            "instance": instance,
        }
        if self.detail:
            out["detail"] = self.detail
        out.update(self.extra)
        return out


class UnconfirmedFacts(ProblemError):
    """409 from POST /determine: the engine is never run on unconfirmed facts."""

    def __init__(self, fields: list[str]) -> None:
        super().__init__(
            code="unconfirmed_facts",
            title="Some facts have not been confirmed",
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Nothing reaches the engine until you confirm it. Confirm or correct the "
                "fields listed, then run the determination again."
            ),
            unconfirmed_fields=fields,
        )


def _json(problem: dict[str, Any], status_code: int) -> JSONResponse:
    return JSONResponse(problem, status_code=status_code, media_type=CONTENT_TYPE)


async def problem_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)
    return _json(exc.body(request.url.path), exc.status_code)


async def http_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limited",
    }.get(exc.status_code, "http_error")
    detail = exc.detail if isinstance(exc.detail, str) else None
    return _json(
        ProblemError(code=code, title=detail or "Request failed", status_code=exc.status_code).body(
            request.url.path
        ),
        exc.status_code,
    )


async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"], "type": e["type"]}
        for e in exc.errors()
    ]
    return _json(
        ProblemError(
            code="validation_failed",
            title="The request body is not valid",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=errors,
        ).body(request.url.path),
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
