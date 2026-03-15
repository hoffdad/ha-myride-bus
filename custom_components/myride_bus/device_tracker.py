from homeassistant.components.device_tracker.config_entry import TrackerEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    trackers = []

    for bus in coordinator.buses:

        trackers.append(MyRideBusTracker(coordinator, bus))

    async_add_entities(trackers)


class MyRideBusTracker(TrackerEntity):

    def __init__(self, coordinator, bus):

        self.coordinator = coordinator
        self.bus = bus
        self._attr_name = f"MyRide Bus {bus}"

    @property
    def latitude(self):
        return self.coordinator.buses[self.bus]["lat"]

    @property
    def longitude(self):
        return self.coordinator.buses[self.bus]["lon"]