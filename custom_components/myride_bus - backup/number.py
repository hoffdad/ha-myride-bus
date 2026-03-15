import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyRideThresholdNumber(NumberEntity, RestoreEntity):
    """Editable threshold number for MyRide status logic."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name, unique_id, default_value):
        self.coordinator = coordinator
        self._key = key
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_value = default_value
        self._attr_native_min_value = 0
        self._attr_native_max_value = 120
        self._attr_native_step = 1
        self._attr_mode = "box"
        self._attr_native_unit_of_measurement = "min"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "settings")},
            name="MyRide Settings",
            manufacturer="Tyler Technologies",
            model="MyRide Configuration",
        )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                restored = int(float(last_state.state))
                self._attr_native_value = restored
            except (TypeError, ValueError):
                pass

        setattr(self.coordinator, self._key, int(self._attr_native_value))
        self.async_write_ha_state()

    async def async_set_native_value(self, value):
        value = int(value)
        self._attr_native_value = value
        setattr(self.coordinator, self._key, value)
        self.coordinator.async_set_updated_data({})
        self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MyRideThresholdNumber(
            coordinator,
            key="enroute_minutes",
            name="Bus Enroute Minutes",
            unique_id="myride_bus_enroute_minutes",
            default_value=20,
        ),
        MyRideThresholdNumber(
            coordinator,
            key="arriving_minutes",
            name="Bus Arriving Minutes",
            unique_id="myride_bus_arriving_minutes",
            default_value=5,
        ),
    ]

    async_add_entities(entities, update_before_add=True)
