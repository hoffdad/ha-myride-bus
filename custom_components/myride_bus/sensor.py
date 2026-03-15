from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []

    for student in coordinator.students.values():

        sensors.append(MyRideETASensor(coordinator, student))

    async_add_entities(sensors)


class MyRideETASensor(SensorEntity):

    def __init__(self, coordinator, student):

        self.coordinator = coordinator
        self.student = student
        self._attr_name = f"{student['name']} Bus ETA"

    @property
    def native_value(self):
        return self.student["eta"]