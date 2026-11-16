#!/usr/bin/env python3
"""Verify firmware overlay dispatch and the resulting ramoops reservation.

Usage: test_rpi_ramoops_map.py OVERLAYS_DIRECTORY BOARD_DTB [BOARD_DTB ...]
Requires fdtget and fdtoverlay from device-tree-compiler.
"""

import pathlib
import subprocess
import sys
import tempfile


def get(dtb, node, prop, kind="x"):
    return subprocess.check_output(
        ["fdtget", "-t", kind, str(dtb), node, prop], text=True
    ).strip()


overlays = pathlib.Path(sys.argv[1])
selected = get(overlays / "overlay_map.dtb", "/ramoops", "bcm2711", "s")
assert selected == "ramoops-pi4", selected
with tempfile.TemporaryDirectory() as tmp:
    for board in map(pathlib.Path, sys.argv[2:]):
        result = pathlib.Path(tmp) / board.name
        subprocess.run(
            ["fdtoverlay", "-i", str(board), "-o", str(result),
             str(overlays / (selected + ".dtbo"))], check=True
        )
        address_cells = int(get(result, "/reserved-memory", "#address-cells"), 16)
        size_cells = int(get(result, "/reserved-memory", "#size-cells"), 16)
        node = "/reserved-memory/ramoops@b000000"
        reg = [int(v, 16) for v in get(result, node, "reg").split()]
        assert len(reg) == address_cells + size_cells, (board, reg)
        address = 0
        for cell in reg[:address_cells]:
            address = (address << 32) | cell
        size = 0
        for cell in reg[address_cells:]:
            size = (size << 32) | cell
        assert address == 0x0B000000 and size == 0x10000, (address, size)
        assert get(result, node, "compatible", "s") == "ramoops"
        assert int(get(result, node, "record-size"), 16) == 0x4000
        print(f"PASS: {board.name}: {selected}, 64 KiB reserved at {address:#x}")
