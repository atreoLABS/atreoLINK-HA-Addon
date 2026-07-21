"""Polls the agent for the current set of notification-eligible members."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AtreoLinkClient, AtreoLinkError, Member
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

type AtreoLinkConfigEntry = ConfigEntry[AtreoLinkCoordinator]


class AtreoLinkCoordinator(DataUpdateCoordinator[dict[str, Member]]):
    """Keeps the member roster fresh; keyed by userId."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AtreoLinkClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Member]:
        try:
            members = await self.client.async_get_members()
        except AtreoLinkError as err:
            raise UpdateFailed(f"could not fetch members: {err}") from err
        return {m.user_id: m for m in members}
