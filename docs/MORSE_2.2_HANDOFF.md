# Morse 2.2 investigation — agent handoff

Updated November 5, 2026 (America/Denver).

## Objective and current result

Upgrade OpenMANET's Morse stack from the 1.8.1-dev baseline to 2.2, retaining
MM6108 SPI at 2.0 where required. Investigate intermittent MM8108 USB startup
failure before treating the new image as ready for deployment. This is a new
branch and disposable test images; the user does not require old-driver fallback
or a "trial driver" path. Preserve settings for the current remote experiments.

The current MM8108 image is **2.2.3-g270da473-diag2**. Mesh and traffic work when
initialization succeeds. **No root cause or production fix has been established.**
One same-image sysupgrade reproduced persistent USB command timeouts, but four
subsequent reflashes succeeded: three with early logging enabled, one disabled.
Do not claim the WM1302 GPS handling caused the failure or that logging fixed it.

## Repositories and work ownership

- Workspace: `/home/ubuntu/openmanet`.
- Firmware: `firmware/`, branch `codex/morse-2.2`, remote `https://github.com/OpenMANET/firmware.git`.
- Existing draft reviews: [firmware #83](https://github.com/OpenMANET/firmware/pull/83),
  [packages #33](https://github.com/OpenMANET/packages/pull/33); originally targeting `1.8.1-dev`.
  Check live PR state before changing either.
- Packages build baseline: `0005a14dcbb3a19bc9459373ab98b9e04e41c7d6`.
- `packages/` is on `fix/halow-gps` with pre-existing changes to SPI reset,
  Morse LuCI configuration/tests, and openmanetd. These were NOT modified or
  committed by this diagnostic handoff. Do not reset or stage them indiscriminately.
- `firmware/feeds/openmanet` has pre-existing driver Makefile edits,
  `040-preserve-ack-timeout.patch` files and tests. Diagnostic builds temporarily
  used recorded recipes, then restored those edits. They are NOT in the tested
  diag2 image. Do not accidentally include them in a reproduction.
- `scripts/morse-2.2/__pycache__/` is generated, not source and not pushed.

## Hardware and access

- manet01: Raspberry Pi CM4, Waveshare CM4-DUAL-ETH-WIFI6-BASE carrier,
  Gateworks MM8108 M.2 radio. Management SSH currently `root@10.41.57.45`.
  User connects from their Mac; direct agent SSH access is not established.
- Radio USB ID `325b:8100`, path `1-1.4`; DWC2 host, hub `1a40:0201`.
- USB Ethernet ID `0bda:8152`, Linux `r8152`, hub port `1-1.5` (10/100).
  The CM4 native Ethernet is the separate Gigabit port.
- manet02: Raspberry Pi 4 with WM1302/Waveshare HAT, xHCI host. Baseline 2.0
  worked; original 2.2 failed USB initialization there too. Recent repeated
  diag2 upgrade tests were on manet01 only.
- Mesh peer manet04: `10.41.187.65`, MAC `2c:c6:82:8a:2b:ca`.
- GPS config on manet01 is `gpsd.core.board=none`. No gpioset processes should
  hold GPIO12/25; both were inputs in verified tests.

## Findings and limitations

Original failures included USB memory writes returning -2 followed by command
-110 timeouts and probe failure. Sometimes the radio subsequently disappeared
from lsusb across reboots, including on restored/fresh 1.8.1-dev. Extended power
removal restored it. This is distinct from the case where USB still enumerates
but the chip stops answering its driver.

The Waveshare schematic shows GPIO12/25 routed to the header, not directly to
M.2 power/reset. Earlier suspicion of direct WM1302 GPIO interference was not
supported by that schematic. Board revision/external wiring still matter.

Source audit found USB read/write and ELF-loader bodies unchanged from 2.0 to
2.2, and reset/clock helpers unchanged apart from names. No missing firmware or
USB frontend was found. Command-completion error propagation and ELF error
handling have weaknesses present in both versions; they are not proven causes.

The diag1 patch added verbose startup tracing. It successfully transferred all
14 firmware segments and initialized the radio. Diag2 retains only USB failure
logging. It adds no explicit delay, timeout, transfer size, firmware, calibration,
or return-value changes. Apply diagnostic patches as ALTERNATIVES, never together.

One later same-image sysupgrade failed. Saved logs start after the initial fault
because coredump reads/timeouts flooded the buffers. They establish command-phase
USB failures, not why the first failure happened. A separate earlier sysupgrade
"Saving config files" hang involved GPS startup/lock handling; do not conflate it
with the post-boot radio failure.

### Latest controlled tests

All use the same diag2 module hash, GPS `none`, and settings-preserving upgrades.

| Test | Early recorder | Result |
|---|---|---|
| Normal reboot baseline | Enabled | Mesh joined at 23.475 s, no USB errors |
| Reflash 1 | Enabled | Mesh joined at 24.082 s; later capture 74 s connected |
| Reflash 2 | Enabled | Mesh joined at 23.722 s; 75 s connected |
| Reflash 3 | Enabled | Mesh joined at 23.779 s; 58 s connected |
| Reflash 4 | Disabled, verified | Mesh joined at 23.385 s; 145 s connected |

Traffic counters and current BATMAN neighbors were present; tx failed was zero.
These are short startup checks, not long-duration stability or throughput tests.
The fourth success weakens, but does not exclude, recorder-induced timing effects.

## Exact image and reproduction

Current image:
`firmware/bin/targets/bcm27xx/bcm2711/diagnostics/openmanet-1.8.1-rpi4-mm8108-usb-morse-2.2.3-diag2-squashfs-sysupgrade.img.gz`

- Image SHA256: `0a424995c408b72f132dfe830e491668d9d2d8721785e973acd4f71092b81708`
- Module SHA256: `da32f2b14b47bb13888422ea322297b897bc13b17aa8d3da057800a5cc21ab5e`
- Driver commit: `270da4733cd4dc62e78e897746f98f6dfb3bef80`
- Firmware commit: `db4b69fd212990c59c5f1712e23060cbb94276ec`
- Firmware file SHA256: `44ebafb072c480f5df1cdd72549893265f23812567ea3777340cdf3217acb72e`
- BCF 0807 SHA256: `263f840958785e0664f6735f605963c352e253bc285dcc30061c48a7371b248a`

Diag1 image retained alongside diag2, SHA256:
`8194f4d578e51473edaefb78d093fcddb2d7b7ccf7293c1f3be85ca9a9560546`.
Original non-diagnostic 2.2 image SHA256:
`5404d380cad4001db96dcca13ce35777dab433b39c9d288b1655e45fae34b540`.

Use the normal `firmware/` buildroot and AGENTS.md. After any clean:
`./scripts/openmanet_setup.sh -i -b ekh-bcm2711`, `make download`, `make -j8`.
Do not return to a separate morse-2.2-builder image workflow.

Exact diag2 package recipes are now versioned under
`scripts/morse-2.2/diagnostics/diag2-recipes/`. Copy them into the corresponding
installed feed package paths only after preserving any existing edits. The
mm8108 recipe's patch named `050-usb-init-diagnostics.patch` actually contains
exactly the failure-only `051-usb-failure-diagnostics.patch` content (historical
build filename). Do not add the verbose 050 patch on top of it.
The saved openmanetd Makefile pins the cached source archive hash, not an immutable
Git commit; preserving that archive is necessary for exact reproduction.

Local logs/recipes/rootfs comparisons: `firmware/logs/morse-2.2/diag2-image/`.
Build, image/rootfs checks, and artifact checks passed when diag2 was built.
Rootfs validation: `python3 scripts/morse-2.2/check-rootfs.py IMAGE usb --diagnostic --diagnostic-version diag2`
(with unsquashfs available). Firmware/BCF match diag1; differences were module,
package metadata and LuCI cache query strings.
`diagnostics/build.py` is the older isolated diag1 module audit helper, NOT the
normal image build command. Images and large build logs remain local artifacts,
not Git-tracked binaries or newly published release assets.

## Early capture tool and current node state

Installer: `scripts/morse-2.2/diagnostics/install-early-capture.sh`.
It installs `/etc/init.d/morse22-early` (START=09, before boot's kmodloader),
`/usr/libexec/morse22-early-reader`, and `/usr/sbin/morse22-collect`.
It preserves the first 16 MiB of /dev/kmsg in RAM without rotation and registers
files/startup links in `/etc/sysupgrade.conf`. Reader does not consume logd's cursor.
Raw output can have a buffered partial final record; collector also saves dmesg
and logread snapshots. Download before reboot/power removal. Reader is not respawned.

Attempt 4 explicitly disabled the service and removed S09/K99 entries from
sysupgrade.conf. Latest verified state: recorder DISABLED. We suggested enabling
it afterward, but have no confirmation the user did so. To restore it fully,
rerun the installer (also restores preservation entries). Merely enabling the
service is not the fully recorded upgrade-preservation setup.

Collect from Mac when enabled:
`ssh root@10.41.57.45 morse22-collect > ~/Downloads/morse22-followup.tgz`

## Evidence files in this workspace

All are under `/home/ubuntu/.codex/attachments/` and are not pushed to Git:

- Original timeout flood: `82e80338-3a31-41c8-9629-fa5e962706e0/morse22-upgrade-failure.log` and `morse22-upgrade-logread.log`.
- Baseline and reflash 1: `6278265d-d146-44a2-bc7a-236323c98ee2/`.
- Later reflash 1: `ea692e91-5c80-4d42-9332-03c02612b8e2/morse22-after-upgrade-later.tgz`.
- Reflash 2: `eb507d33-4ce0-4bee-83c6-0e3990c718cd/morse22-upgrade-attempt2.tgz`.
- Reflash 3: `109c1ad4-8add-4d74-aa35-cf996e885830/morse22-upgrade-attempt3.tgz`.
- Reflash 4: `9977648b-cc6f-4969-8386-2a2dbf2f5585/morse22-attempt4-no-recorder.txt`.

## Public research

Closest report: [very-srs/MANET #13](https://github.com/very-srs/MANET/issues/13),
October 23, 2026: CM4/MM8108 persistent USB -110 errors until power cycle,
log flood erases trigger. Open with no replies when checked. Kernel 6.18.33,
driver version unspecified, failure after 8.5 hours; NOT a confirmed same-root-cause
or upgrade-triggered bug. Proposal is fault detection, not a proven reset fix.

[Morse forum startup report](https://community.morsemicro.com/t/mm8108-usb-interface-failed-to-start-ap-and-use-the-morse-cli/1781)
concerns missing morse_cli transport support, a different symptom.
No matching confirmed fix found in MorseMicro/morse_driver issues. No issue or
forum post was created during this investigation.

## Next steps / automated bench

1. Preserve this known image and comparison evidence. Do not call four passes a fix.
2. Restore early logging before further attempts intended to capture the trigger.
   Record whether each attempt is reboot, same-image upgrade, or full power removal.
3. Obtain a first-failure capture, then compare shutdown/reinitialization sequences.
   A USB reset or changed delay is an experiment, not an established recovery.
4. Extend successful testing to sustained bidirectional traffic and longer uptime;
   test manet02 separately. Do not treat iw's mapped VHT rate as measured HaLow throughput.
5. User wants an agent-operated loop: normal local build, image transfer/checksum,
   settings-preserving flash, reconnect, USB/mesh checks, automatic evidence collection.
   Needs SSH key/network access from build workspace to a designated disposable node,
   management Ethernet independent of HaLow, and ideally switched power that truly
   removes node/radio power. No such access/power integration has been configured.
6. Agree the target node, settings policy, attempt limit, and stop-on-failure behavior
   before unattended cycling. User welcomes automation but has not provided the
   credentials/network endpoint for agent access or a power controller.

Do not merge the draft reviews or publish a production release as part of handoff.
