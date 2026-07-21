"""Tests for the atreoLINK integration's API client.

api.py has no Home Assistant dependencies, so it is loaded directly by path
(bypassing the package __init__, which imports homeassistant). The client is
exercised against a real in-process aiohttp server rather than a mock, so the
actual request path — URL, auth header, JSON body — is covered. Run from the
repo root with:

    uv run --python 3.13 --with aiohttp --with pytest --with pytest-asyncio \
        --no-project pytest tests
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

_API_PATH = (
    Path(__file__).resolve().parents[1] / "custom_components" / "atreolink" / "api.py"
)
_spec = importlib.util.spec_from_file_location("atreolink_api", _API_PATH)
assert _spec and _spec.loader
api = importlib.util.module_from_spec(_spec)
# Register before exec so dataclass(slots=True) can resolve its own module.
sys.modules["atreolink_api"] = api
_spec.loader.exec_module(api)


class _Recorder:
    def __init__(self) -> None:
        self.requests: list[dict] = []


@contextlib.asynccontextmanager
async def _running_agent(routes: list[tuple[str, str, int, dict]]):
    """Spin up a throwaway agent that records requests and returns canned JSON.

    routes: (method, path, status, payload) tuples.
    """
    rec = _Recorder()
    app = web.Application()

    def _make(status: int, payload: dict):
        async def handler(request: web.Request) -> web.Response:
            body = None
            if request.body_exists:
                with contextlib.suppress(Exception):
                    body = await request.json()
            rec.requests.append(
                {
                    "method": request.method,
                    "path": request.path,
                    "auth": request.headers.get("Authorization"),
                    "json": body,
                }
            )
            return web.json_response(payload, status=status)

        return handler

    for method, path, status, payload in routes:
        app.router.add_route(method, path, _make(status, payload))

    server = TestServer(app)
    await server.start_server()
    try:
        yield server, rec
    finally:
        await server.close()


def _client(session: aiohttp.ClientSession, server: TestServer) -> api.AtreoLinkClient:
    return api.AtreoLinkClient(session, server.host, server.port, "secret-key")


@pytest.mark.asyncio
async def test_get_members_parses_and_skips_keyless() -> None:
    body = {
        "members": [
            {"userId": "u1", "name": "Alice", "email": "a@x.com", "role": "admin"},
            {"name": "NoId", "email": "n@x.com", "role": "member"},
        ]
    }
    async with (
        _running_agent([("GET", "/v1/members", 200, body)]) as (srv, rec),
        aiohttp.ClientSession() as s,
    ):
        members = await _client(s, srv).async_get_members()
    assert len(members) == 1
    assert members[0].user_id == "u1"
    assert members[0].name == "Alice"
    assert rec.requests[0]["auth"] == "Bearer secret-key"


@pytest.mark.asyncio
async def test_send_by_email_builds_payload() -> None:
    async with (
        _running_agent([("POST", "/v1/notify", 200, {"sent": True})]) as (
            srv,
            rec,
        ),
        aiohttp.ClientSession() as s,
    ):
        await _client(s, srv).async_send(
            title="T", body="B", email="a@x.com", severity="warning"
        )
    assert rec.requests[0]["json"] == {
        "title": "T",
        "body": "B",
        "severity": "warning",
        "userEmail": "a@x.com",
    }


@pytest.mark.asyncio
async def test_send_by_user_id_includes_html() -> None:
    async with (
        _running_agent([("POST", "/v1/notify", 200, {"sent": True})]) as (
            srv,
            rec,
        ),
        aiohttp.ClientSession() as s,
    ):
        await _client(s, srv).async_send(
            title="T", body="B", user_id="u1", html="<p>hi</p>"
        )
    sent = rec.requests[0]["json"]
    assert sent["userId"] == "u1"
    assert sent["html"] == "<p>hi</p>"
    assert "userEmail" not in sent


@pytest.mark.asyncio
async def test_401_maps_to_auth_error() -> None:
    async with (
        _running_agent([("GET", "/v1/members", 401, {})]) as (srv, _rec),
        aiohttp.ClientSession() as s,
    ):
        with pytest.raises(api.AtreoLinkAuthError):
            await _client(s, srv).async_get_members()


@pytest.mark.asyncio
async def test_404_maps_to_unsupported_error() -> None:
    async with (
        _running_agent([("GET", "/v1/members", 404, {})]) as (srv, _rec),
        aiohttp.ClientSession() as s,
    ):
        with pytest.raises(api.AtreoLinkUnsupportedError):
            await _client(s, srv).async_get_members()
