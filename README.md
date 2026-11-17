# CyncMyself

A Home Assistant custom integration for GE Cync (C by GE) switches, plugs, bulbs and fan switches, tuned for large setups where the Cync cloud gets overloaded.

## Credit

CyncMyself is based on [cync_lights](https://github.com/nikshriv/cync_lights) by **[@nikshriv](https://github.com/nikshriv)**, who reverse-engineered the Cync cloud protocol and built the original integration. All of the device support, login flow and protocol work is his. This repository starts from his last release (commit `9dba8ed`, April 2025) and is maintained separately from it. If the original helped you, you can thank him at https://www.buymeacoffee.com/nikshriv.

## What's different

The original integration sends every command the moment Home Assistant asks for it, and resends any unacknowledged command every 0.5 s. A scene that changes a dozen lights can therefore send dozens of packets within a few seconds, and the Cync server responds by dropping commands, answering minutes late, or resetting the connection. CyncMyself paces that traffic. These changes are in `custom_components/cync_lights/cync_hub.py`:

- **Send queue.** Every light command and retry goes through one queue and leaves at least 0.25 s after the previous one. The gap is `SEND_SPACING` at the top of the file. Acknowledgements to the Cync server, pings and state requests skip the queue and go out right away, so a busy scene can't hold them up.
- **Stale retries are dropped.** When a newer command arrives for a light, any older retries for that light stop, including ones still waiting in the queue. A retry of an old command can no longer undo a newer one.
- **Slower retries.** An unacknowledged command is resent every 1.5 s for up to 6 s (4 attempts), instead of every 0.5 s for up to 5 s (10 attempts).
- **Retry timer starts after sending.** The wait for an acknowledgement includes the time a packet spends in the queue, so a backlog does not set off extra retries.

A scene that changes 11 lights now takes about 3 seconds to send instead of going out in one burst.

Setup and options changes (in `config_flow.py`):

- **Setup selects individual switches by default.** The original pre-selected every Cync room and group but only fans as switches, which creates a light entity per room instead of per device. CyncMyself pre-selects every switch, bulb and plug and leaves rooms and groups unticked. You can still tick rooms or groups if you want them.
- **Configure works without signing in again.** Answering "No" to "Reauthorize?" in the integration's Configure dialog used to crash (a 500 error). It now goes straight to device selection.

The integration domain is still `cync_lights`, so it replaces the original in place: existing entities, automations and dashboards keep working.

## Requirements

- At least one Wi-Fi connected Cync device. Bluetooth-only devices are controlled through a Wi-Fi device; a setup with only Bluetooth devices will not work.
- The primary Cync account. Secondary (shared) accounts are not supported.
- Motion and ambient light sensors work on 4-wire switches only. 3-wire switches and the wireless motion sensor do not report their state to the Cync server.

## Installation

1. If the original cync_lights is installed through HACS, remove its repository from HACS first. This leaves your configured integration in place.
2. In HACS, add a custom repository: URL `https://github.com/Woodhead02/CyncMyself`, category **Integration**.
3. Download it and do a full Home Assistant restart.
4. If this is a new install, go to **Settings → Devices & services → Add integration**, choose Cync, sign in with your Cync email and password, and enter the code Cync emails you. Every switch, bulb and plug is ticked by default; untick anything you don't want. To change the selection later, open the integration's **Configure** and answer "No" to "Reauthorize?".
