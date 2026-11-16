#!/usr/bin/env python3
"""Apply the boot profile's UART overlays to real Pi DTBs and check routing.

Usage: test_rpi_bluetooth_uart.py BCM2710_DTS_DIR BCM2711_DTS_DIR [CONFIG]
Model filters follow Raspberry Pi's documented table:
https://www.raspberrypi.com/documentation/computers/config_txt.html#conditional-filters
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / 'target/linux/bcm27xx/image/boards/ekh01/distroconfig.txt'


def effective(board_type, filters):
    active = True
    result = []
    for raw in CONFIG.read_text().splitlines():
        line = raw.strip()
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
            if section.startswith('board-type='):
                active = int(section.split('=', 1)[1], 0) == board_type
            else:
                active = section == 'all' or section in filters
        elif active and line and not line.startswith('#'):
            result.append(line)
    return result


def get(dtb, node, prop, kind='s', optional=False):
    result = subprocess.run(['fdtget', '-t', kind, str(dtb), node, prop],
                            text=True, capture_output=True)
    if optional and result.returncode:
        return None
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


cases = [
    ('Pi3B', 0x8, {'pi3'}, 0, 'bcm2710-rpi-3-b.dtb', True),
    ('Pi3B+', 0xd, {'pi3', 'pi3+'}, 0, 'bcm2710-rpi-3-b-plus.dtb', True),
    ('Pi3A+', 0xe, {'pi3', 'pi3+'}, 0, 'bcm2710-rpi-3-b-plus.dtb', True),
    ('Zero2W', 0x12, {'pi0', 'pi0w', 'pi02'}, 0, 'bcm2710-rpi-zero-2-w.dtb', True),
    ('CM3', 0xa, {'pi3', 'cm3'}, 0, 'bcm2710-rpi-cm3.dtb', False),
    ('CM3+', 0x10, {'pi3', 'pi3+', 'cm3+'}, 0, 'bcm2710-rpi-cm3.dtb', False),
    ('Pi2-1.2', 0x4, {'pi2'}, 0, 'bcm2710-rpi-2-b.dtb', False),
    ('Pi4', 0x11, {'pi4'}, 1, 'bcm2711-rpi-4-b.dtb', True),
    ('CM4', 0x14, {'pi4', 'cm4'}, 1, 'bcm2711-rpi-cm4.dtb', True),
]
with tempfile.TemporaryDirectory() as directory:
    for name, board_type, filters, index, filename, native_bt in cases:
        settings = effective(board_type, filters)
        assert 'enable_uart=1' in settings, name
        assert 'uart_enable=1' not in settings, name
        assert 'dtoverlay=uart5' not in settings, name
        uart_overlays = [line.split('=', 1)[1].split(',', 1)[0]
                         for line in settings if line.startswith('dtoverlay=')
                         and line.split('=', 1)[1].split(',', 1)[0] in
                         ('uart1', 'disable-bt', 'miniuart-bt')]
        source = pathlib.Path(sys.argv[index + 1]) / filename
        result = pathlib.Path(directory) / (name + '.dtb')
        if uart_overlays:
            overlays = [source.parent.parent / 'overlays' / (overlay + '.dtbo')
                        for overlay in uart_overlays]
            subprocess.run(['fdtoverlay', '-i', str(source), '-o', str(result),
                            *map(str, overlays)], check=True)
        else:
            result.write_bytes(source.read_bytes())
        uart0 = get(result, '/__symbols__', 'uart0')
        uart1 = get(result, '/__symbols__', 'uart1')
        if native_bt:
            assert uart_overlays == ['uart1'], (name, uart_overlays)
            assert get(result, '/aliases', 'serial0') == uart1, name
            assert get(result, uart1, 'status') == 'okay', name
            pins = get(result, '/__symbols__', 'uart1_pins')
            assert get(result, pins, 'brcm,pins', 'u') == '14 15', name
            assert get(result, uart0 + '/bluetooth', 'status', optional=True) != 'disabled', name
            bt_pins = get(result, '/__symbols__', 'uart0_pins')
            assert not ({14, 15} & set(map(int, get(result, bt_pins, 'brcm,pins', 'u').split()))), name
            if index == 0:
                assert 'core_freq=250' in settings, name
        else:
            assert not uart_overlays, (name, uart_overlays)
            assert get(result, '/aliases', 'serial0') == uart0, name
            assert 'core_freq=250' not in settings, name
        print(f'PASS: {name}: native BT + header mini UART' if native_bt else
              f'PASS: {name}: existing PL011 header UART retained')

pi3_patches = ROOT / 'patches/ekh-bcm2710'
for patch in (ROOT / 'patches/ekh-bcm2711').glob('*.patch'):
    assert (pi3_patches / patch.name).read_bytes() == patch.read_bytes(), patch.name
print('PASS: RPi3 receives the same Bluetooth consent and service fixes as RPi4')
