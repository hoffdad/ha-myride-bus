import logging
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyRideBaseStudentSensor(CoordinatorEntity):
    """Base class for student sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, student):
        super().__init__(coordinator)
        self.student_unique = student["student_unique"]
        self.student_name = student["name"]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"student_{self.student_unique}")},
            name=f"MyRide {self.student_name}",
            manufacturer="Tyler Technologies",
            model="MyRide Student",
        )

    @property
    def student(self):
        """Return the latest student data."""
        for s in self.coordinator.students.values():
            if s["student_unique"] == self.student_unique:
                return s
        return None


class MyRideETAMinutesSensor(MyRideBaseStudentSensor, SensorEntity):
    """Sensor for ETA in minutes."""

    def __init__(self, coordinator, student):
        super().__init__(coordinator, student)
        self._attr_name = "Bus Minutes"
        self._attr_unique_id = f"myride_student_{self.student_unique}_minutes"

    @property
    def native_value(self):
        student = self.student
        if not student:
            return None

        eta_str = student.get("eta")
        if not eta_str:
            return None

        try:
            if eta_str.endswith("Z"):
                eta_str = eta_str.replace("Z", "+00:00")

            eta_time = datetime.fromisoformat(eta_str)
            now = datetime.now(timezone.utc)
            minutes = int((eta_time - now).total_seconds() / 60)
            return max(minutes, 0)

        except Exception as e:
            _LOGGER.warning("Failed parsing ETA minutes for %s: %s", self.student_name, e)
            return None


class MyRideETAClockSensor(MyRideBaseStudentSensor, SensorEntity):
    """Sensor showing ETA time."""

    def __init__(self, coordinator, student):
        super().__init__(coordinator, student)
        self._attr_name = "Bus ETA"
        self._attr_unique_id = f"myride_student_{self.student_unique}_eta"

    @property
    def native_value(self):
        student = self.student
        if not student:
            return None

        eta_str = student.get("eta")
        if not eta_str:
            return None

        try:
            if eta_str.endswith("Z"):
                eta_str = eta_str.replace("Z", "+00:00")

            eta_time = datetime.fromisoformat(eta_str)
            return eta_time.astimezone().isoformat()

        except Exception as e:
            _LOGGER.warning("Failed calculating ETA clock for %s: %s", self.student_name, e)
            return None


class MyRideBusStatusSensor(MyRideBaseStudentSensor, SensorEntity):
    """Sensor describing bus arrival status."""

    def __init__(self, coordinator, student):
        super().__init__(coordinator, student)
        self._attr_name = "Bus Status"
        self._attr_unique_id = f"myride_student_{self.student_unique}_status"

    @property
    def native_value(self):
        student = self.student
        if not student:
            return "no_bus"

        eta_str = student.get("eta")
        if not eta_str:
            return "no_bus"

        try:
            if eta_str.endswith("Z"):
                eta_str = eta_str.replace("Z", "+00:00")

            eta_time = datetime.fromisoformat(eta_str)
            now = datetime.now(timezone.utc)
            minutes = max(int((eta_time - now).total_seconds() / 60), 0)

            arriving_threshold = int(self.coordinator.arriving_minutes)
            enroute_threshold = int(self.coordinator.enroute_minutes)

            if minutes <= arriving_threshold:
                return "arriving"
            if minutes <= enroute_threshold:
                return "enroute"
            return "scheduled"

        except Exception:
            return "no_bus"


class MyRideBaseBusSensor(CoordinatorEntity, SensorEntity):
    """Base class for bus sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator)
        self.bus_id = bus_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"bus_{bus_id}")},
            name=f"MyRide Bus {bus_id}",
            manufacturer="Tyler Technologies",
            model="MyRide Bus",
        )

    @property
    def bus(self):
        return self.coordinator.buses.get(self.bus_id)


class MyRideBusLastUpdateSensor(MyRideBaseBusSensor):
    """Sensor showing last update time for a bus."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_name = "Last Update"
        self._attr_unique_id = f"myride_bus_{bus_id}_last_update"

    @property
    def native_value(self):
        bus = self.bus
        if not bus:
            return None
        return bus.get("last_update")


class MyRideBusSpeedSensor(MyRideBaseBusSensor):
    """Sensor showing current speed for a bus."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_name = "Speed"
        self._attr_unique_id = f"myride_bus_{bus_id}_speed"
        self._attr_native_unit_of_measurement = "mph"

    @property
    def native_value(self):
        bus = self.bus
        if not bus:
            return None
        return bus.get("speed")


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up student sensors and dynamic bus sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    created_bus_sensors = set()

    for student in coordinator.students.values():
        sensors.append(MyRideETAMinutesSensor(coordinator, student))
        sensors.append(MyRideETAClockSensor(coordinator, student))
        sensors.append(MyRideBusStatusSensor(coordinator, student))

    async_add_entities(sensors, update_before_add=True)

    def add_new_bus_sensors():
        new_entities = []

        for bus_id in coordinator.buses:
            if bus_id not in created_bus_sensors:
                created_bus_sensors.add(bus_id)
                new_entities.append(MyRideBusLastUpdateSensor(coordinator, bus_id))
                new_entities.append(MyRideBusSpeedSensor(coordinator, bus_id))

        if new_entities:
            async_add_entities(new_entities)

    add_new_bus_sensors()
    coordinator.async_add_listener(add_new_bus_sensors)
