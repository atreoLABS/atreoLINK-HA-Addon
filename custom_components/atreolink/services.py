"""The generic ``atreolink.send_notification`` service.

Complements the per-member notify entities: accepts one or more recipient
emails in a single call and carries fields the notify entity can't (severity,
HTML body), so it suits templated automations and multi-recipient alerts.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import AtreoLinkError
from .const import (
    ATTR_HTML,
    ATTR_MESSAGE,
    ATTR_SEVERITY,
    ATTR_TARGETS,
    ATTR_TITLE,
    DEFAULT_SEVERITY,
    DOMAIN,
    SERVICE_SEND_NOTIFICATION,
    SEVERITIES,
)
from .coordinator import AtreoLinkCoordinator

SEND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TARGETS): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(ATTR_TITLE): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_SEVERITY, default=DEFAULT_SEVERITY): vol.In(SEVERITIES),
        vol.Optional(ATTR_HTML): cv.string,
    }
)


def _coordinator(hass: HomeAssistant) -> AtreoLinkCoordinator:
    """Return the coordinator of the single loaded atreoLINK entry."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("atreoLINK is not set up")
    return entries[0].runtime_data


async def _async_send(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _coordinator(hass)
    client = coordinator.client
    failures: list[str] = []
    for email in call.data[ATTR_TARGETS]:
        try:
            await client.async_send(
                title=call.data[ATTR_TITLE],
                body=call.data[ATTR_MESSAGE],
                email=email,
                severity=call.data[ATTR_SEVERITY],
                html=call.data.get(ATTR_HTML),
            )
        except AtreoLinkError as err:
            failures.append(f"{email}: {err}")
    if failures:
        raise ServiceValidationError(
            "Some notifications failed: " + "; ".join(failures)
        )


def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_NOTIFICATION):
        return

    async def handler(call: ServiceCall) -> None:
        await _async_send(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_NOTIFICATION, handler, schema=SEND_SCHEMA
    )
