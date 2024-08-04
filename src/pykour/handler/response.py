import json
from http import HTTPStatus
from typing import Any

from pykour.request import Request
from pykour.response import Response
import pykour.exceptions as ex


def determine_content_type_for_response_body(request: Request, response_body: Any) -> str:
    for accept in request.accept:
        if accept == "text/plain":
            return accept
        if accept == "application/json":
            return accept
        if accept == "*/*":
            if isinstance(response_body, dict):
                return "application/json"
            return "text/plain"
    return "text/plain"


def determine_content_type_for_error_response(request: Request) -> str:
    for accept in request.accept:
        if accept == "application/json":
            return accept
    return "text/plain"


def detect_error_phrase(response: Response, phrase: str) -> str:
    if response.content_type == "application/json":
        return json.dumps({"error": phrase})
    return phrase


def detect_response_body(request: Request, response: Response, response_body: Any) -> None:
    app = request.app

    if response.status == HTTPStatus.NO_CONTENT:
        response.content = ""
    elif request.method == "OPTIONS":
        response.add_header("Allow", ", ".join(app.get_allowed_methods(request.path)))
        response.content = ""
    elif request.method == "HEAD":
        response.add_header("Content-Length", str(len(str(response_body))))
        response.content = ""
    elif response.content_type == "application/json":
        response.content = json.dumps(response_body)
    elif response.content_type == "text/plain":
        response.content = str(response_body)


async def handle_response(request: Request, response: Response, response_body: Any) -> None:
    response.content_type = determine_content_type_for_response_body(request, response_body)
    detect_response_body(request, response, response_body)
    await response.render()


async def handle_error(request: Request, response: Response, status: HTTPStatus) -> None:
    response.content_type = determine_content_type_for_error_response(request)
    response.status = status
    response.content = detect_error_phrase(response, status.phrase)
    await response.render()


async def handle_http_exception(request: Request, response: Response, e: ex.HTTPException) -> None:
    response.content_type = determine_content_type_for_error_response(request)
    response.status = e.status_code
    response.content = detect_error_phrase(response, e.message)
    await response.render()