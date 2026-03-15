import logging
from datetime import datetime, timezone
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .websocket import MyRideWebsocket
from .api import MyRideAPI
from .auth import MyRideAuth

_LOGGER = logging.getLogger(__name__)


class MyRideCoordinator(DataUpdateCoordinator):
    """Coordinator for MyRide K-12 integration."""

    def __init__(self, hass: HomeAssistant, config: dict):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="myride",
            update_method=self._dummy_update,
            update_interval=None,
        )

        self.hass = hass
        self.username = config["username"]
        self.password = config["password"]

        self.auth = MyRideAuth()
        self.token = None

        self.students = {}
        self.buses = {}

        self.enroute_minutes = 20
        self.arriving_minutes = 5

    async def _dummy_update(self):
        """Dummy update for coordinator initialization."""
        return {}

    async def async_setup(self):
        """Set up the coordinator: get token, discover tenant, fetch students, start WebSocket."""
        try:
            self.token = await self.auth.get_token(self.username, self.password)
        except Exception as e:
            _LOGGER.error("Failed to get MyRide auth token: %s", e)
            return

        api = MyRideAPI(self.token)

        try:
            await api.discover_tenant()
            _LOGGER.info("MyRide tenant detected: %s", api.tenant_id)
        except Exception as e:
            _LOGGER.error("Failed to discover tenant: %s", e)
            return

        try:
            students = await api.get_students()
        except Exception as e:
            _LOGGER.error("Failed to fetch students: %s", e)
            return

        for s in students:
            student_id = s["studentId"]
            student_unique = s["uniqueId"]

            run_info = s.get("runInfo") or []
            run = run_info[0] if run_info else None

            route_name = run.get("visibleName") if run else None
            bus_number = run.get("busNumber") if run else None
            rollout_bus_number = run.get("rolloutBusNumber") if run else None
            active_vehicle = run.get("activeVehicle") if run else None
            asset_unique_id = run.get("assetUniqueId") if run else None
            driver_name = run.get("driverName") if run else None
            rollout_driver_name = run.get("rolloutDriverName") if run else None
            is_current_run = run.get("isCurrentRun") if run else None
            vehicle_status = run.get("vehicleStatus") if run else None
            run_detail = run.get("runDetail") if run else []
            stops_info = run.get("stopsInfo") if run else []

            self.students[student_id] = {
                "name": f'{s["firstName"]} {s["lastName"]}',
                "student_unique": student_unique,
                "grade": s.get("gradeName"),
                "school": s.get("locationName"),
                "route_name": route_name,
                "bus_number": bus_number,
                "bus_id": asset_unique_id,
                "default_stop": None,
                "override_stop": None,
                "eta": None,
            }

            if asset_unique_id:
                existing = self.buses.get(asset_unique_id, {})
                self.buses[asset_unique_id] = {
                    "lat": existing.get("lat"),
                    "lon": existing.get("lon"),
                    "speed": existing.get("speed"),
                    "last_update": existing.get("last_update"),
                    "route": route_name,
                    "bus_number": bus_number,
                    "rollout_bus_number": rollout_bus_number,
                    "active_vehicle": active_vehicle,
                    "driver_name": driver_name,
                    "rollout_driver_name": rollout_driver_name,
                    "current_run": is_current_run,
                    "vehicle_status": vehicle_status,
                    "stop_count": len(stops_info) if stops_info else len(run_detail),
                    "current_stop_id": existing.get("current_stop_id"),
                    "current_stop": existing.get("current_stop"),
                    "stops_info": stops_info,
                }

        ws = MyRideWebsocket(self.token, self.handle_ws)
        try:
            self.hass.async_create_task(ws.start())
            _LOGGER.info("MyRide WebSocket started successfully")
        except Exception as e:
            _LOGGER.error("Failed to start MyRide WebSocket: %s", e)

    async def handle_ws(self, data: dict):
        """Handle incoming WebSocket data."""
        try:
            updated = False

            if data.get("type") == 1 and "target" in data:
                if data["target"] == "NewLocation":
                    loc = data["arguments"][0]
                    bus = str(loc["assetUniqueId"])

                    existing = self.buses.get(bus, {})
                    if bus not in self.buses:
                        updated = True

                    self.buses[bus] = {
                        "lat": loc.get("latitude"),
                        "lon": loc.get("longitude"),
                        "speed": loc.get("speed"),
                        "last_update": datetime.now(timezone.utc).isoformat(),
                        "route": existing.get("route"),
                        "bus_number": existing.get("bus_number"),
                        "rollout_bus_number": existing.get("rollout_bus_number"),
                        "active_vehicle": existing.get("active_vehicle"),
                        "driver_name": existing.get("driver_name"),
                        "rollout_driver_name": existing.get("rollout_driver_name"),
                        "current_run": existing.get("current_run"),
                        "vehicle_status": existing.get("vehicle_status"),
                        "stop_count": existing.get("stop_count"),
                        "current_stop_id": existing.get("current_stop_id"),
                        "current_stop": existing.get("current_stop"),
                        "stops_info": existing.get("stops_info", []),
                    }

                    updated = True

                if data["target"] == "NewETA":
                    eta = data["arguments"][0]
                    stop_id = eta.get("stopId")
                    eta_value = eta.get("eta")

                    for student in self.students.values():
                        active_stop = student["override_stop"] or student["default_stop"]
                        if stop_id == active_stop:
                            student["eta"] = eta_value
                            updated = True

                        # Fallback: if stop matching isn't wired yet, still allow
                        # route/bus metadata to be used later when needed.

                    # Update bus current stop by matching the stop ID against known routes
                    for bus_id, bus_data in self.buses.items():
                        stops_info = bus_data.get("stops_info") or []
                        for stop in stops_info:
                            if stop.get("stopId") == stop_id:
                                bus_data["current_stop_id"] = stop_id
                                bus_data["current_stop"] = (
                                    stop.get("stopDescription")
                                    or stop.get("locationName")
                                    or stop.get("stopAddress")
                                )
                                updated = True
                                break

            if updated:
                self.async_set_updated_data({})

        except Exception as e:
            _LOGGER.error("Error processing WebSocket message: %s", e)
