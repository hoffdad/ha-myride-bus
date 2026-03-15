import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyRideBusTracker(CoordinatorEntity, TrackerEntity):
    """Tracker for a single bus."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bus"

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator)
        self.bus_id = bus_id

        self._attr_name = "Location"
        self._attr_unique_id = f"myride_bus_{bus_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"bus_{bus_id}")},
            name=f"MyRide Bus {bus_id}",
            manufacturer="MyRide K-12",
            model="Bus",
        )

    @property
    def latitude(self):
        bus = self.coordinator.buses.get(self.bus_id)
        return bus["lat"] if bus else None

    @property
    def longitude(self):
        bus = self.coordinator.buses.get(self.bus_id)
        return bus["lon"] if bus else None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up bus trackers dynamically."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    created_buses = set()

    def add_new_buses():
        new_entities = []

        for bus_id in coordinator.buses:
            if bus_id not in created_buses:
                created_buses.add(bus_id)
                new_entities.append(MyRideBusTracker(coordinator, bus_id))

        if new_entities:
            async_add_entities(new_entities)

    add_new_buses()
    coordinator.async_add_listener(add_new_buses)
