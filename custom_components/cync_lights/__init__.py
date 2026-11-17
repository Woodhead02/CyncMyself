"""The Cync Room Lights integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN
from .cync_hub import CyncHub

PLATFORMS: list[str] = ["light","binary_sensor","switch","fan"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cync Room Lights from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    remove_options_update_listener = entry.add_update_listener(options_update_listener)
    hub = CyncHub(entry.data, entry.options, remove_options_update_listener)
    hass.data[DOMAIN][entry.entry_id] = hub
    hub.start_tcp_client()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "report_stats"):
        def hubs():
            return [h for h in hass.data.get(DOMAIN, {}).values() if hasattr(h, "report_stats")]

        async def set_send_spacing(call: ServiceCall) -> None:
            for h in hubs():
                h.send_spacing = call.data["seconds"]

        async def report_stats(call: ServiceCall) -> ServiceResponse:
            return {"hubs": [h.report_stats() for h in hubs()]}

        hass.services.async_register(DOMAIN, "set_send_spacing", set_send_spacing,
            schema=vol.Schema({vol.Required("seconds"): vol.All(vol.Coerce(float), vol.Range(min=0, max=2))}))
        hass.services.async_register(DOMAIN, "report_stats", report_stats,
            supports_response=SupportsResponse.OPTIONAL)

    return True

async def options_update_listener(
    hass: HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hub = hass.data[DOMAIN][entry.entry_id]
    hub.remove_options_update_listener()
    hub.disconnect()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
