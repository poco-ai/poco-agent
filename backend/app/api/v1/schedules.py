import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.observability.request_context import get_request_id, get_trace_id
from app.core.settings import get_settings
from app.schemas.response import Response, ResponseSchema

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=ResponseSchema[dict])
async def get_schedules() -> JSONResponse:
    """Proxy schedules from Executor Manager for frontend display."""
    settings = get_settings()
    url = f"{settings.executor_manager_url}/api/v1/schedules"

    try:
        headers = {
            "accept": "application/json",
            "X-Internal-Token": settings.internal_api_token,
        }
        request_id = get_request_id()
        if request_id:
            headers["X-Request-ID"] = request_id
        trace_id = get_trace_id()
        if trace_id:
            headers["X-Trace-ID"] = trace_id
        request = Request(url, headers=headers)
        with urlopen(request, timeout=3) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        return Response.success(data=data, message="Schedules retrieved")
    except HTTPError as e:
        raise AppException(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=f"Executor Manager schedules request failed: {e.code}",
        ) from e
    except URLError as e:
        raise AppException(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=f"Executor Manager unavailable: {e.reason}",
        ) from e
    except Exception as e:
        raise AppException(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=f"Failed to fetch schedules from Executor Manager: {e}",
        ) from e
