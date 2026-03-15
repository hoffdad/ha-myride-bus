from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant

from .websocket import MyRideWebsocket
from .api import MyRideAPI

class MyRideCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, config):

        super().__init__(hass, None, name="myride")

        self.hass = hass
        self.token = config["token"]

        self.students = {}
        self.buses = {}

    async def async_setup(self):

        api = MyRideAPI(self.token)

        students = await api.get_students()

        for s in students:

            self.students[s["studentId"]] = {
                "name": s["firstName"],
                "default_stop": s["stopId"],
                "override_stop": None,
                "eta": None
            }

        ws = MyRideWebsocket(self.token, self.handle_ws)

        self.hass.loop.create_task(ws.start())

    async def handle_ws(self, data):

        if data.get("target") == "NewLocation":

            loc = data["arguments"][0]

            bus = loc["assetUniqueId"]

            self.buses[bus] = {
                "lat": loc["latitude"],
                "lon": loc["longitude"],
                "speed": loc["speed"]
            }

        if data.get("target") == "NewETA":

            eta = data["arguments"][0]

            stop = eta["stopId"]

            for student in self.students.values():

                active_stop = student["override_stop"] or student["default_stop"]

                if stop == active_stop:

                    student["eta"] = eta["eta"]

        self.async_set_updated_data({})