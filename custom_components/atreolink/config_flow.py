"""Config flow for the atreoLINK integration.

Two entry points:
- ``async_step_hassio``: the add-on publishes host/port/api_key via Supervisor
  discovery, so the user just confirms.
- ``async_step_user``: manual entry (paste the key from the add-on Log tab, or
  point at a standalone agent on the LAN).
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import (
    AtreoLinkAuthError,
    AtreoLinkClient,
    AtreoLinkConnectionError,
    AtreoLinkUnsupportedError,
)
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
)


class AtreoLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for atreoLINK."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    async def _validate(self, data: dict[str, Any]) -> str | None:
        """Return an error key, or None if the agent answered correctly."""
        client = AtreoLinkClient(
            async_get_clientsession(self.hass),
            data[CONF_HOST],
            data[CONF_PORT],
            data[CONF_API_KEY],
        )
        try:
            await client.async_get_members()
        except AtreoLinkAuthError:
            return "invalid_auth"
        except AtreoLinkUnsupportedError:
            return "unsupported_agent"
        except AtreoLinkConnectionError:
            return "cannot_connect"
        return None

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery published by the atreoLINK add-on."""
        config = discovery_info.config
        data = {
            CONF_HOST: config.get(CONF_HOST, DEFAULT_HOST),
            CONF_PORT: config.get(CONF_PORT, DEFAULT_PORT),
            CONF_API_KEY: config.get(CONF_API_KEY, ""),
        }
        await self.async_set_unique_id(DOMAIN)
        # Re-published on every add-on start, so a rotated key updates in place.
        self._abort_if_unique_id_configured(updates=data)
        self._discovered = data
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm setup of a discovered agent."""
        if user_input is None:
            return self.async_show_form(step_id="hassio_confirm")

        if error := await self._validate(self._discovered):
            return self.async_show_form(
                step_id="hassio_confirm", errors={"base": error}
            )
        return self.async_create_entry(title="atreoLINK", data=self._discovered)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            if error := await self._validate(user_input):
                errors["base"] = error
            else:
                return self.async_create_entry(title="atreoLINK", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(user_input or {}).get(CONF_HOST, DEFAULT_HOST),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT),
                ): int,
                vol.Required(
                    CONF_API_KEY,
                    default=(user_input or {}).get(CONF_API_KEY, ""),
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
