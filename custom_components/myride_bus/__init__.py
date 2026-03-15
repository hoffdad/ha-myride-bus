from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MyRideCoordinator

PLATFORMS = ["sensor", "device_tracker"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    coordinator = MyRideCoordinator(hass, entry.data)

    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True