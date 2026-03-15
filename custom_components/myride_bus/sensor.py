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
            manufacturer="MyRide K-12",
            model="Student",
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
        self._attr_translation_key = "bus_minutes"
        self._attr_unique_id = f"myride_student_{self.student_unique}_minutes"
        self._attr_icon = "mdi:timer-outline"

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
        self._attr_translation_key = "bus_eta"
        self._attr_unique_id = f"myride_student_{self.student_unique}_eta"
        self._attr_icon = "mdi:clock-outline"

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
        self._attr_translation_key = "bus_status"
        self._attr_unique_id = f"myride_student_{self.student_unique}_status"

    @property
    def icon(self):
        state = self.native_value
        if state == "arriving":
            return "mdi:bus-marker"
        if state == "enroute":
            return "mdi:bus"
        if state == "scheduled":
            return "mdi:bus-clock"
        return "mdi:bus-alert"

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


class MyRideSchoolSensor(MyRideBaseStudentSensor, SensorEntity):
    """Student school sensor."""

    def __init__(self, coordinator, student):
        super().__init__(coordinator, student)
        self._attr_translation_key = "school"
        self._attr_unique_id = f"myride_student_{self.student_unique}_school"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        student = self.student
        return student.get("school") if student else None


class MyRideStudentRouteNameSensor(MyRideBaseStudentSensor, SensorEntity):
    """Student route name sensor."""

    def __init__(self, coordinator, student):
        super().__init__(coordinator, student)
        self._attr_translation_key = "route_name"
        self._attr_unique_id = f"myride_student_{self.student_unique}_route_name"
        self._attr_icon = "mdi:map-marker-path"

    @property
    def native_value(self):
        student = self.student
        return student.get("route_name") if student else None


class MyRideBaseBusSensor(CoordinatorEntity, SensorEntity):
    """Base class for bus sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator)
        self.bus_id = bus_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"bus_{bus_id}")},
            name=f"MyRide Bus {bus_id}",
            manufacturer="MyRide K-12",
            model="Bus",
        )

    @property
    def bus(self):
        return self.coordinator.buses.get(self.bus_id)


class MyRideBusLastUpdateSensor(MyRideBaseBusSensor):
    """Bus last update sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "bus_last_update"
        self._attr_unique_id = f"myride_bus_{bus_id}_last_update"
        self._attr_icon = "mdi:update"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("last_update") if bus else None


class MyRideBusSpeedSensor(MyRideBaseBusSensor):
    """Bus speed sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "bus_speed"
        self._attr_unique_id = f"myride_bus_{bus_id}_speed"
        self._attr_native_unit_of_measurement = "mph"
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("speed") if bus else None


class MyRideBusRouteSensor(MyRideBaseBusSensor):
    """Bus route sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "bus_route"
        self._attr_unique_id = f"myride_bus_{bus_id}_route"
        self._attr_icon = "mdi:map-marker-path"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("route") if bus else None


class MyRideBusNumberSensor(MyRideBaseBusSensor):
    """Bus number sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "bus_number"
        self._attr_unique_id = f"myride_bus_{bus_id}_bus_number"
        self._attr_icon = "mdi:numeric"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("bus_number") if bus else None


class MyRideRolloutBusNumberSensor(MyRideBaseBusSensor):
    """Rollout bus number sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "rollout_bus_number"
        self._attr_unique_id = f"myride_bus_{bus_id}_rollout_bus_number"
        self._attr_icon = "mdi:numeric"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("rollout_bus_number") if bus else None


class MyRideActiveVehicleSensor(MyRideBaseBusSensor):
    """Active vehicle sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "active_vehicle"
        self._attr_unique_id = f"myride_bus_{bus_id}_active_vehicle"
        self._attr_icon = "mdi:bus-multiple"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("active_vehicle") if bus else None


class MyRideDriverNameSensor(MyRideBaseBusSensor):
    """Driver name sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "driver_name"
        self._attr_unique_id = f"myride_bus_{bus_id}_driver_name"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("driver_name") if bus else None


class MyRideRolloutDriverNameSensor(MyRideBaseBusSensor):
    """Rollout driver name sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "rollout_driver_name"
        self._attr_unique_id = f"myride_bus_{bus_id}_rollout_driver_name"
        self._attr_icon = "mdi:account-switch"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("rollout_driver_name") if bus else None


class MyRideCurrentRunSensor(MyRideBaseBusSensor):
    """Current run sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "current_run"
        self._attr_unique_id = f"myride_bus_{bus_id}_current_run"
        self._attr_icon = "mdi:check-circle-outline"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("current_run") if bus else None


class MyRideVehicleStatusSensor(MyRideBaseBusSensor):
    """Vehicle status sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "vehicle_status"
        self._attr_unique_id = f"myride_bus_{bus_id}_vehicle_status"
        self._attr_icon = "mdi:information-outline"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("vehicle_status") if bus else None


class MyRideStopCountSensor(MyRideBaseBusSensor):
    """Stop count sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "stop_count"
        self._attr_unique_id = f"myride_bus_{bus_id}_stop_count"
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("stop_count") if bus else None


class MyRideCurrentStopSensor(MyRideBaseBusSensor):
    """Current stop sensor."""

    def __init__(self, coordinator, bus_id):
        super().__init__(coordinator, bus_id)
        self._attr_translation_key = "current_stop"
        self._attr_unique_id = f"myride_bus_{bus_id}_current_stop"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self):
        bus = self.bus
        return bus.get("current_stop") if bus else None


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up student sensors and dynamic bus sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    created_bus_sensors = set()

    for student in coordinator.students.values():
        sensors.append(MyRideETAMinutesSensor(coordinator, student))
        sensors.append(MyRideETAClockSensor(coordinator, student))
        sensors.append(MyRideBusStatusSensor(coordinator, student))
        sensors.append(MyRideSchoolSensor(coordinator, student))
        sensors.append(MyRideStudentRouteNameSensor(coordinator, student))

    async_add_entities(sensors, update_before_add=True)

    def add_new_bus_sensors():
        new_entities = []

        for bus_id in coordinator.buses:
            if bus_id not in created_bus_sensors:
                created_bus_sensors.add(bus_id)
                new_entities.extend(
                    [
                        MyRideBusLastUpdateSensor(coordinator, bus_id),
                        MyRideBusSpeedSensor(coordinator, bus_id),
                        MyRideBusRouteSensor(coordinator, bus_id),
                        MyRideBusNumberSensor(coordinator, bus_id),
                        MyRideRolloutBusNumberSensor(coordinator, bus_id),
                        MyRideActiveVehicleSensor(coordinator, bus_id),
                        MyRideDriverNameSensor(coordinator, bus_id),
                        MyRideRolloutDriverNameSensor(coordinator, bus_id),
                        MyRideCurrentRunSensor(coordinator, bus_id),
                        MyRideVehicleStatusSensor(coordinator, bus_id),
                        MyRideStopCountSensor(coordinator, bus_id),
                        MyRideCurrentStopSensor(coordinator, bus_id),
                    ]
                )

        if new_entities:
            async_add_entities(new_entities)

    add_new_bus_sensors()
    coordinator.async_add_listener(add_new_bus_sensors)
