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

1. **WM1302 HAT GPS/GNSS** — `patches/ekh-bcm2712/0007` and `0010` are still
   unexercised on hardware.
2. **NVMe** — deferred.
3. `build-ekh-bcm2712` is still not wired into `build-release.yml`.

Authoritative state: `PI5_PORT_STATUS.md`.
