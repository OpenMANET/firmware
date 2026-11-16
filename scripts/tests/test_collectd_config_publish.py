#!/usr/bin/env python3
"""Exercise real start_service wrappers while a launched reader opens config.

Usage: test_collectd_config_publish.py ORIGINAL_INIT PATCHED_INIT
The old wrapper must reproduce missing reads; the fixed one must not.
"""
import pathlib
import subprocess
import sys
import tempfile
import threading
import time


def exercise(path):
    source = pathlib.Path(path).read_text()
    body = source.split('start_service() {', 1)[1].split('\n}', 1)[0]
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        config = root / 'collectd.conf'
        config.write_text('complete\n')
        target = root / 'generated.conf'
        target.write_text('complete\n')
        stop = threading.Event()
        counts = [0, 0, 0]

        def reader():
            while not stop.is_set():
                try:
                    if config.read_text() != 'complete\n':
                        counts[2] += 1
                except FileNotFoundError:
                    counts[0] += 1
                counts[1] += 1
                time.sleep(0.0002)

        thread = threading.Thread(target=reader)
        thread.start()
        script = r'''
COLLECTD_CONF="$1/collectd.conf"
process_config() {
    rm -f "$COLLECTD_CONF"
    sleep 0.002
    ln -s "$1" "$COLLECTD_CONF"
}
procd_open_instance() { :; }
procd_set_param() { :; }
procd_append_param() { :; }
procd_close_instance() { :; }
'''.replace('ln -s "$1"', 'ln -s "' + str(target) + '"')
        script += '\nstart_service() {\n' + body + '\n}\n'
        script += 'i=0; while [ "$i" -lt 100 ]; do start_service || exit; i=$((i+1)); done\n'
        try:
            subprocess.run(['sh', '-c', script, 'test', directory], check=True)
        finally:
            stop.set()
            thread.join()
        assert counts[1] > 0
        assert counts[2] == 0, 'reader saw an incomplete configuration'
        return counts[0]


old, new = map(exercise, sys.argv[1:3])
assert old > 0, 'negative control did not reproduce the missing config'
assert new == 0, f'patched startup still lost config {new} times'
print(f'Original: {old} missing config reads; patched: {new}')
