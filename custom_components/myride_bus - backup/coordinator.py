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
            self.students[student_id] = {
                "name": f'{s["firstName"]} {s["lastName"]}',
                "student_unique": s["uniqueId"],
                "grade": s["gradeName"],
                "school": s["locationName"],
                "default_stop": None,
                "override_stop": None,
                "eta": None,
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
                    bus = loc["assetUniqueId"]

                    if bus not in self.buses:
                        updated = True

                    self.buses[bus] = {
                        "lat": loc["latitude"],
                        "lon": loc["longitude"],
                        "speed": loc["speed"],
                        "last_update": datetime.now(timezone.utc).isoformat(),
                    }

                    updated = True

                if data["target"] == "NewETA":
                    eta = data["arguments"][0]
                    stop = eta["stopId"]

                    for student in self.students.values():
                        active_stop = student["override_stop"] or student["default_stop"]
                        if stop == active_stop:
                            student["eta"] = eta["eta"]
                            updated = True

            if updated:
                self.async_set_updated_data({})

        except Exception as e:
            _LOGGER.error("Error processing WebSocket message: %s", e)
