# Last Claude Report — Raspberry Pi 5 Port, Session 5

Date: 2026-08-30
Branch: `pi5-wm6108-port` · Baseline: `365b276`
Mode: UART operator — every software action below was performed over the 3-pin
JST-SH console (`.ai-workflow/pi5-uart.ps1`, COM4). No owner keystrokes were needed
apart from supplying the mesh passphrase.

# §14 PHASE 1 REGRESSION — COMPLETE, HARDWARE VERIFIED

The Pi4↔Pi5 HaLow mesh is restored and re-verified on the current image, with the
RTL8822BU running healthy at SuperSpeed at the same time.

## Result vs. the original Phase 1 run

| Check | Phase 1 (2026-08-28) | §14 re-verification |
|---|---|---|
| `wlh0` type | mesh point | **mesh point** |
| Peer | `a8:dd:9f:4d:c0:e3` | **`a8:dd:9f:4d:c0:e3`** (same unit) |
| mesh plink | ESTAB | **ESTAB** |
| authorized / authenticated / associated | yes | **yes / yes / yes** |
| signal | ~ −46 dBm | **−35 to −38 dBm** |
| expected throughput | ~7.52 Mbps | **7.52 Mbps** |
| `batctl if` | wlh0 active | **wlh0: active** |
| routing algo | BATMAN_V | **BATMAN_V** |
| BATMAN neighbour / originator | via `wlh0`, ~7.2 | **via `wlh0`, 7.2 / 7.1** |
| end-to-end ping | 4/4, 0%, 3.620/3.892/4.105 ms | **4/4, 0%, 3.854/3.950/4.075 ms** |

Beyond the original run: `batctl gwl` shows the Pi 4 as a live **gateway**
(10.0/2.0 MBit) and the station dump reports `mesh connected to gate: yes`. After a
reboot the mesh re-formed **unattended** at boottime 24.6 s, with BATMAN resolving
the peer by name as `RAPTOR-01_wlh0`; post-reboot ping **10/10, 0% loss,
3.886/4.828/10.316 ms**. That is a stronger result than Phase 1, which was
provisioned live rather than cold-booted. The chronic
`alfred: can't get interface` spam is gone now that `bat0` exists.

All preservation requirements held: country **US**, channel **42 / 923.0 MHz**,
**`bcf_fgh100mhaamd.bin`**, `mesh_id=openmanet`, 802.11s, **BATMAN_V**.

## How it was provisioned

I applied the LuCI EKH wizard's **Mesh Point / bridge** transformation as a scripted
`uci` sequence, from the source analysis in `PI5_PORT_STATUS.md`, and deliberately
did **not** replay the wizard's destructive global resets. So the firewall rule set,
the wan zone's REJECT posture and the stock forwardings all survived — running the
real wizard would have wiped them.

`br-lan` was replaced by `br-ahwlan{eth0, bat0}`, `lan` left deviceless (no
`10.41.0.0/16` collision), and the RTL8822BU AP moved onto `ahwlan`. Full pre-change
backup remains at `/root/cfgbak/`.

One deliberate deviation: the wizard writes `mesh11sd.mesh_params.nolearn`, which is
a dead option — the shipped config and `morse.sh` both use `mesh_nolearn`. I wrote
the working name.

## Two behaviours worth knowing

**openmanetd rewrites the `ahwlan` address.** My pinned `10.41.254.15` was replaced
with `10.41.183.117` and written back into UCI by openmanetd's
`AddressReservationWorker`. That is the product's own mesh-wide address reservation
working as designed — the wizard's random IP is only a seed, not a final value.

**One unexplained reboot.** The unit rebooted once mid-verification with no recorded
cause: `/sys/fs/pstore` empty, no under-voltage, OOM, panic, hung task or RCU stall,
and 7.9 GB of 8 GB RAM free. It happened while a 254-process ping sweep (used to find
the Pi 4's address) overlapped a netifd reconfiguration, and the cmdline carries
`reboot=w` with procd's watchdog active — so a watchdog reset triggered by my own
diagnostic sweep is the most plausible explanation. **I could not prove it.** It did
not recur and the box returned with the mesh fully working, but it should not be
written off as explained.

## Next hardware-validation areas (unchanged)

1. **WM1302 HAT GPS/GNSS** — done on 2026-08-30; see the GNSS section below.
2. **NVMe** — deferred.
3. `build-ekh-bcm2712` is still not wired into `build-release.yml`.

Authoritative state: `PI5_PORT_STATUS.md`.

---

# WM1302 GNSS VALIDATION — SOFTWARE VERIFIED, fix pending antenna (2026-08-30)

Both target patches are now exercised on Pi 5 hardware. No code changes were needed
or made.

## Software chain verified: `/dev/ttyAMA0` → u-blox → gpsd → openmanetd

GPSD reports `"driver":"u-blox"`, `9600 8N1`, `"native":1`, activated on
`/dev/ttyAMA0` — and `native:1` means gpsd successfully *switched* the receiver into
binary mode, which the receiver must accept, so this is two-way communication rather
than passive listening. A 400-message capture over ~200 s yielded 199 TPV and 198 SKY
at a steady ~1 Hz with no dropouts. openmanetd logs `INF gps Connected to GPSD`.

The GPS UART (`ttyAMA0`, 204,64) is distinct from our debug console (`ttyAMA10`,
204,74), so there is no contention between GNSS and the UART operator workflow.

## Patch 0007 — VALIDATED

The boot log shows `configuring GPS GPIOs (RST=25, WAKE=12)` and
`pulsing GPS reset on GPIO25`. Reaching those lines *is* the proof:
`check_morse_device` calls `exit 0` unless the morse radio path suffix-matches
`spi_master/spi0/spi0.0`, and the live path is
`platform/axi/1000120000.pcie/1f00050000.spi/spi_master/spi0/spi0.0` — which the old
BCM2711-literal comparison would have rejected, killing the script before any GPIO
work.

`gpioinfo` shows GPIO25/GPIO12 held as outputs with `consumer="gps-wm1302"` by two
live `gpioset` daemons (pids 2017, 2020), which fully explains the `?` readback. Left
alone, as instructed.

**One correction worth recording:** the patch comment justifies avoiding
`-c gpiochip0` by asserting RP1 "is not gpiochip0" on BCM2712. On this kernel that is
not true — `gpiodetect` shows `gpiochip0 [pinctrl-rp1] (54 lines)` with brcmstb at
`gpiochip10..13`. The `--by-name` fix is still correct (name resolution is
enumeration-order independent), but the comment's specific predicted failure did not
occur and should not be cited as demonstrated.

## Patch 0010 — VALIDATED

`/tmp/sysinfo/board_name` = `bcm2712,mm6108-spi`, and that string is present in the
shipped binary. `supported_features.go:39` puts `BCM2712_MM6108_SPI` in the
`GNSSsupoorted()` true-case; without the patch it would hit `default: return false`.

The functional proof: `openmanet.go:86` creates the GPS service — and its `gps`
logger — only inside `if cfg.GetEnableGNSS() && board.GNSSsupoorted()`. The live
`INF gps Connected to GPSD` line cannot appear unless that returned true.

## No satellite fix — environmental, not a software regression

All 199 TPV reports are `mode:1`, and **none of the 198 SKY reports contained a
`satellites` array**, with all DOPs at 0.00. So the receiver is tracking *zero*
satellites rather than failing to resolve a fix from weak ones. That is category A
(receiver and software working, no signal), not category B.

Zero satellites in view is a stronger symptom than a marginal indoor attempt, where a
few low-C/N0 satellites would normally still be listed. I cannot narrow it further
from software: `ubxtool` is not in the image, so UBX-MON-HW antenna status
(OK/OPEN/SHORT) is unreadable, and `gpsmon` is a curses UI unsuitable for a serial
console.

| Item | State |
|---|---|
| Software path | **VERIFIED** |
| Hardware receiver communication | **VERIFIED** |
| Patch 0007 | **VERIFIED on Pi 5** |
| Patch 0010 | **VERIFIED on Pi 5** |
| Satellite fix | **PENDING** — antenna |

## Owner action required

Give the GNSS antenna clear sky visibility, and while you are at the unit confirm it
is seated in the WM1302's **GNSS** connector rather than the LoRa one. I will resume
monitoring over UART automatically on your confirmation.

---

# GNSS UPDATE — SATELLITE FIX OBTAINED, validation COMPLETE (2026-08-30)

Antenna moved to a closed window via ~7 ft of segmented coax (roughly seven 1-foot
sections with multiple inline connectors). **A valid 3D fix was acquired and held.**

| Item | Value |
|---|---|
| TPV mode | **3 (3D fix)** |
| Lat / lon | **present** (values not recorded) |
| Altitude | **available** (`altHAE`, `altMSL`, `alt`) |
| Satellites used / visible | **not reportable** — see correction below |
| Time to first fix | ~5–6 min after antenna placement |
| Fix held | **8 min 41 s continuous**, 1044 consecutive mode-3 reports |
| Stability | monotonic — all 454 mode-1 reports precede all 1044 mode-3; no reversion |

**Independent corroboration:** the receiver reported UTC `2026-08-30T06:57:08.999Z`
— the correct real date — while the system clock still read `Jun 24 2025`. Correct
UTC date cannot be produced without decoding satellite navigation messages.

**The RF chain degraded but did not defeat the fix.** DOP improved 3–4× as the
receiver converged: hdop 4.08 → **1.57**, pdop 8.18 → **2.29**, vdop 7.08 → **1.67**.
Position accuracy stayed coarse (eph ~75 m, epv ~165 m), which is what you'd expect
from that many inline connectors plus glass — but it acquired and held.

**openmanetd reception verified.** `alfred -r 102` shows two node records: the Pi 4
(`RAPTOR-01`, 10.41.254.142) with no position field, and this Pi 5
(`BCM2712-3f76`, 10.41.183.117) carrying an embedded 23-byte protobuf submessage
with two float64s — latitude and longitude. openmanetd has the fix and is publishing
position across the BATMAN mesh:

```
/dev/ttyAMA0 → u-blox → gpsd → openmanetd → alfred → mesh
```

## Correction to my earlier reading

I previously reported the receiver was "tracking zero satellites" because no SKY
message contained a `satellites` array. **That inference was wrong.** SKY still has
no `satellites` array now, with a 3D fix active — gpsd's u-blox driver simply does
not emit per-satellite data (UBX-NAV-SAT) for this receiver configuration, so the
array's absence says nothing about tracking.

The meaningful indicator was the DOP values all being 0.00 (no solution), now
non-zero. My conclusion at the time — category A, environmental rather than a
software fault — was correct, but the reasoning I gave for it was not. Satellite
counts remain unavailable from this image because `ubxtool` is not installed.

## Final GNSS status

| Item | State |
|---|---|
| Software path | **VERIFIED** |
| Hardware receiver communication | **VERIFIED** |
| Patch 0007 | **VERIFIED on Pi 5** |
| Patch 0010 | **VERIFIED on Pi 5** |
| Satellite fix | **VERIFIED — 3D acquired and held** |
| openmanetd reception + mesh publication | **VERIFIED** |

No software changes were required at any point.

## One observation for later (not a blocker)

The system clock is not disciplined from GNSS — it read `2025-06-24` while the
receiver had correct `2026-08-30` UTC. Worth deciding whether gpsd should set system
time on these units, since mesh-wide log timestamps are currently wrong.
