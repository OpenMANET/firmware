# OpenMANET 1.8-eu2 test images

This build fixes the LuCI channel selector used by the EU mesh experiment.
For an enabled EU/GB HaLow mesh interface, it offers fixed 1 MHz channels
and removes `auto`. It also repairs an old `auto` or 2 MHz choice when the
mesh frequency form is opened. AP/STA channel policy remains unchanged.

## Images

- `openmanet-1.8-eu2-halowlink2-mm8108-squashfs-sysupgrade.bin`:
  HaLowLink 2, MM8108 SDIO.
- `openmanet-1.8-eu2-rpi4-mm8108-usb-squashfs-sysupgrade.img.gz`:
  Raspberry Pi 4 / CM4 with an MM8108 USB radio, such as Gateworks GW16167.
  This is not an image for an MM6108 SPI/SDIO HAT.

Check each download against `SHA256SUMS.txt` before flashing. The firmware,
packages and LuCI source revisions are recorded in `BUILD_INFO.json`.

## Two-node test

1. Back up any configuration you need, then install the image matching each
   device. For this baseline test, clear the previous configuration and do
   not restore a backup. Hard-refresh the browser after the upgrade.
2. In the normal LuCI setup, select country **EU**, then the **802.11s Mesh
   Wizard**. The image label does not change the normal first-boot defaults;
   select EU explicitly.
3. Verify that bandwidth is **1 MHz** and that fixed channels are offered.
   The EU channel table lists 1, 3, 5, 7 and 9; hardware filtering may limit
   availability. Select the same available fixed channel on both nodes
   (for example 5 at 865.5 MHz). `auto` must not be offered for EU mesh.
4. Use matching mesh IDs, SAE security and passphrases. Configure one node
   as the mesh gate with an Ethernet uplink and the other as a mesh point.
   Apply the wizard before changing advanced settings.
5. Verify that the mesh interface appears, a peer connects, and traffic
   passes. Reopen the frequency form and check that the fixed channel is
   retained. Restart the radios and repeat the peer/traffic check.

The existing EU startup checks still require automatic duty cycling in
spread mode, 1 MHz bandwidth, and a configured TX power from 0 to 16 dBm.
Actual radiated power depends on antenna gain and cable loss. Low duty-cycle
limits apply to mesh management and relayed traffic as well as user data.

## If the test fails

Capture these read-only diagnostics on both nodes before changing settings:

```sh
ubus call system board
uci show wireless
iw dev
wifi status
logread
```

Redact passphrases from `uci show wireless` and sensitive information from
logs before sharing. If `iw dev` shows the HaLow mesh interface, substitute
its actual name for `wlh0` in:

```sh
morse_cli -i wlh0 channel
morse_cli -i wlh0 duty_cycle
morse_cli -i wlh0 health
iw dev wlh0 station dump
batctl if
batctl n
```

## Validation scope

The image verifier checks original build checksums, the pinned netifd and
radio defaults, MM8108 firmware 2.2.3, and the version label. It executes
the channel selector regression test against the minified widget extracted
from each image, including selection, save/reload and country changes.

These checks do not establish successful multi-node operation on the new
images or RF compliance. Those still require hardware testing.
