"""Per-member notify entities.

One ``notify.*`` entity is created for each notification-eligible family
member the agent reports. Entities appear and disappear as the coordinator's
roster changes.
"""

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AtreoLinkError
from .const import DOMAIN
from .coordinator import AtreoLinkConfigEntry, AtreoLinkCoordinator

DEFAULT_TITLE = "Home Assistant"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AtreoLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up notify entities and keep them in sync with the roster."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_members() -> None:
        new = [uid for uid in coordinator.data if uid not in known]
        if not new:
            return
        known.update(new)
        async_add_entities(
            AtreoLinkNotifyEntity(coordinator, entry.entry_id, uid) for uid in new
        )

    _add_new_members()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_members))


class AtreoLinkNotifyEntity(CoordinatorEntity[AtreoLinkCoordinator], NotifyEntity):
    """A notify target that delivers to one atreoLINK member."""

    _attr_has_entity_name = True
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(
        self,
        coordinator: AtreoLinkCoordinator,
        entry_id: str,
        user_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._user_id = user_id
        self._attr_unique_id = f"{entry_id}_{user_id}"
        self._attr_name = coordinator.data[user_id].name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="atreoLINK",
            manufacturer="atreoLABS",
        )

    @property
    def available(self) -> bool:
        """Unavailable once the member drops off the roster."""
        return super().available and self._user_id in self.coordinator.data

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Deliver an end-to-end-encrypted push to this member."""
        try:
            await self.coordinator.client.async_send(
                title=title or DEFAULT_TITLE,
                body=message,
                user_id=self._user_id,
            )
        except AtreoLinkError as err:
            raise HomeAssistantError(f"atreoLINK notify failed: {err}") from err
