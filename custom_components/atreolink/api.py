"""Thin async client for the atreoAGENT local notification API."""

from __future__ import annotations

from dataclasses import dataclass

import aiohttp


class AtreoLinkError(Exception):
    """Base error for the atreoLINK API client."""


class AtreoLinkAuthError(AtreoLinkError):
    """The API key was rejected (HTTP 401)."""


class AtreoLinkConnectionError(AtreoLinkError):
    """The agent could not be reached."""


class AtreoLinkUnsupportedError(AtreoLinkError):
    """The agent is reachable but too old to list members (HTTP 404)."""


@dataclass(frozen=True, slots=True)
class Member:
    """A notification-eligible family member as reported by the agent."""

    user_id: str
    name: str
    email: str
    role: str


class AtreoLinkClient:
    """Talks to the agent's Bearer-authenticated notify API over the LAN."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        api_key: str,
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def async_get_members(self) -> list[Member]:
        """Return the members the agent can currently deliver notifications to."""
        data = await self._request("GET", "/v1/members")
        members = data.get("members", []) if isinstance(data, dict) else []
        return [
            Member(
                user_id=m.get("userId", ""),
                name=m.get("name", ""),
                email=m.get("email", ""),
                role=m.get("role", ""),
            )
            for m in members
            if m.get("userId")
        ]

    async def async_send(
        self,
        *,
        title: str,
        body: str,
        user_id: str | None = None,
        email: str | None = None,
        severity: str = "info",
        html: str | None = None,
    ) -> None:
        """Send one notification to a single member (by user_id or email)."""
        payload: dict[str, str] = {
            "title": title,
            "body": body,
            "severity": severity,
        }
        if user_id:
            payload["userId"] = user_id
        elif email:
            payload["userEmail"] = email
        else:
            raise AtreoLinkError("one of user_id or email is required")
        if html:
            payload["html"] = html
        await self._request("POST", "/v1/notify", json=payload)

    async def _request(
        self, method: str, path: str, *, json: dict | None = None
    ) -> object:
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                headers=self._headers,
                json=json,
            ) as resp:
                if resp.status == 401:
                    raise AtreoLinkAuthError("API key rejected by the agent")
                if resp.status == 404:
                    raise AtreoLinkUnsupportedError(
                        "agent does not support this endpoint; update the add-on"
                    )
                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                return {}
        except aiohttp.ClientResponseError as err:
            raise AtreoLinkError(f"agent returned HTTP {err.status}") from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AtreoLinkConnectionError(str(err)) from err
