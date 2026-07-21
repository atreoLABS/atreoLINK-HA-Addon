"""The atreoLINK integration.

Bundled with the atreoLINK Home Assistant add-on. Exposes one notify entity per
family member plus a generic ``atreolink.send_notification`` service for
templated, multi-recipient or severity-tagged messages.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AtreoLinkClient
from .const import CONF_API_KEY, CONF_HOST, CONF_PORT
from .coordinator import AtreoLinkConfigEntry, AtreoLinkCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: AtreoLinkConfigEntry) -> bool:
    """Set up atreoLINK from a config entry."""
    client = AtreoLinkClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_API_KEY],
    )
    coordinator = AtreoLinkCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AtreoLinkConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
