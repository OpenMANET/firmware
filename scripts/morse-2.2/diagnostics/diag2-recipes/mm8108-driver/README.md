# Morse MM8108 driver 2.2.3

`kmod-mm8108` is the normal MM8108 driver on this branch. It builds USB and
SDIO support into `morse.ko`, including dot11ah. There is no separate shim
package or old-driver selection. `kmod-mm6108` supplies the MM6108 SPI/SDIO
variant and cannot share an image with this module.

The driver and firmware sources are pinned in their package Makefiles.
The firmware repository records the complete image build and hardware checks
in `docs/MORSE_2.2.md`.

Regulatory discovery tests exercise the patched driver C code:

```sh
python3 tests/regdom.py /path/to/patched/driver/source
```
