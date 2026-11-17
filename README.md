# CyncMyself

A Home Assistant custom integration for GE Cync (C by GE) switches, plugs, bulbs and fan switches, tuned for large setups where the Cync cloud gets overloaded.

## Credit

CyncMyself is based on [cync_lights](https://github.com/nikshriv/cync_lights) by **[@nikshriv](https://github.com/nikshriv)**, who reverse-engineered the Cync cloud protocol and built the original integration. All of the device support, login flow and protocol work is his. This repository starts from his last release (commit `9dba8ed`, April 2025) and is maintained separately from it. If the original helped you, you can thank him at https://www.buymeacoffee.com/nikshriv.

## What's different

The original integration sends every command the moment Home Assistant asks for it, and resends any unacknowledged command every 0.5 s. A scene that changes a dozen lights can therefore send dozens of packets within a few seconds, and the Cync server responds by dropping commands, answering minutes late, or resetting the connection. CyncMyself paces that traffic. These changes are in `custom_components/cync_lights/cync_hub.py`:

- **Send queue.** Every light command and retry goes through one queue and leaves at least 0.05 s after the previous one. The gap is `SEND_SPACING` at the top of the file. Acknowledgements to the Cync server, pings and state requests skip the queue and go out right away, so a busy scene can't hold them up.
- **Stale retries are dropped.** When a newer command arrives for a light, any older retries for that light stop, including ones still waiting in the queue. A retry of an old command can no longer undo a newer one.
- **Color temperature turns the bulb on.** Setting a color temperature on an off bulb (as scenes do) used to change nothing, and any brightness in the same command was ignored. The bulb is now switched on at the requested brightness first, then set to the color temperature. The two packets have separate sequence numbers, and the command is retried until the server acknowledges both.
- **Slower retries.** An unacknowledged command is resent every 1.5 s for up to 9 s (6 attempts), instead of every 0.5 s for up to 5 s (10 attempts). If a light still hasn't acknowledged, a warning naming the light is written to the Home Assistant log.
- **Checks that the light actually changed.** The Cync server acknowledges a command when it receives it, not when the light carries it out. After the acknowledgement, CyncMyself waits up to 3 s for the light to report the requested on/off state and brightness, and resends the command if it doesn't. A light that never reports the right state gets a warning in the log.
- **Color works on its own and with brightness.** Setting a color on an off bulb turns it on at full brightness (it used to stay off), and a color sent with a brightness now applies both (the color used to be dropped).
- **Retry timer starts after sending.** The wait for an acknowledgement includes the time a packet spends in the queue, so a backlog does not set off extra retries.
- **No lost status messages.** The original read the server's stream in 1000-byte chunks and threw away any packet split across two chunks, then read the following bytes out of alignment. Status updates, including the full state sent at startup, were lost or misread, so lights could show the wrong state or flick between on and off in Home Assistant. Partial packets are now kept until the rest arrives.
- **Faster sends.** Rate testing found the Cync server accepts bursts with no gap at all, so the default gap between packets is now 0.05 s instead of 0.25 s.
- **Returns as soon as the server answers.** Each attempt used to wait a fixed 1.5 s before checking for an acknowledgement. It now carries on the moment every packet is acknowledged (typically about 0.2 s), and only waits the full 1.5 s when one is missing.
- **Fewer state writes.** The server repeats each light's status many times a second. Home Assistant is now only told when something actually changed.
- **Better startup state.** The full mesh state is requested from every connected Wi-Fi controller instead of one, since each only knows the Bluetooth devices it can reach, and status messages arriving as either message type are understood. Unrecognised messages are written to the debug log to help track down anything still missing.
- **Rate diagnostics.** Two services help tune the send rate. `cync_lights.set_send_spacing` (field `seconds`) changes the gap between queued packets until Home Assistant restarts. `cync_lights.report_stats` returns and logs what happened since the last report: packets sent, acknowledged and unacknowledged, stale retries dropped, connection resets, acknowledgement latency, and the longest queue backlog. Calling it resets the counters.

A scene that changes 11 lights goes out in about half a second, paced rather than in one burst.

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
