import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MyRideCoordinator

PLATFORMS = ["sensor", "device_tracker", "number"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MyRide Bus from a config entry."""
    _LOGGER.info(
        "Setting up MyRide Bus integration for user: %s",
        entry.data.get("username"),
    )

    coordinator = MyRideCoordinator(hass, entry.data)

    try:
        await coordinator.async_setup()
    except Exception as e:
        _LOGGER.error("MyRide coordinator setup failed: %s", e)
        return False

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("MyRide Bus integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload MyRide Bus config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
