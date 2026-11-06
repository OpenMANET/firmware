#!/usr/bin/env python3
"""Compile an isolated diagnostic module with the recorded image's Kbuild command.
Does not modify installed feeds, image outputs, or the normal driver build directory.
"""
import hashlib, os, pathlib, shlex, subprocess
root = pathlib.Path(__file__).resolve().parents[3]
source = root / 'build_dir/morse22-diagnostic/diagnostic'
archive = root / 'dl/mm8108-driver-270da4733cd4dc62e78e897746f98f6dfb3bef80.tar.zst'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '5960e498da1ce76c4aa4e126ff13fe1ab97a47954ca3500598895072b186346d'
# Require a new destination so stale sources or patches cannot enter the build.
if source.exists():
    raise SystemExit(f'{source} already exists; move it aside before rebuilding')
source.mkdir(parents=True)
subprocess.run(['tar', '--zstd', '-xf', str(archive), '--strip-components=1', '-C', str(source)], check=True)
feed = root / 'feeds/openmanet'
prefix = '0005a14dcbb3a19bc9459373ab98b9e04e41c7d6:morse-micro/mm8108-driver/patches'
patches = subprocess.check_output(['git', '-C', str(feed), 'ls-tree', '--name-only', prefix], text=True).splitlines()
for name in patches:
    data = subprocess.check_output(['git', '-C', str(feed), 'show', prefix + '/' + name])
    subprocess.run(['patch', '--batch', '-p1'], cwd=source, input=data, check=True)
subprocess.run(['patch', '--batch', '-p1', '-i', str(pathlib.Path(__file__).with_name('050-usb-init-diagnostics.patch'))], cwd=source, check=True)
lines = (root / 'logs/morse-2.2/build-final.log').read_text().splitlines()
line = next(x for x in lines if x.startswith('make MORSE_VERSION="2.2.3-g270da473"'))
args = shlex.split(line)
old_source = next(x[2:] for x in args if x.startswith('M='))
args = [x.replace(old_source, str(source)) for x in args if not x.startswith('--jobserver-auth=')]
args = ['MORSE_VERSION=2.2.3-g270da473-diag1' if x.startswith('MORSE_VERSION=') else x for x in args]
args.insert(1, '-j8')
env = os.environ.copy()
env['PATH'] = str(root / 'staging_dir/toolchain-aarch64_cortex-a72_gcc-13.3.0_musl/bin') + ':' + env['PATH']
env['STAGING_DIR'] = str(root / 'staging_dir/target-aarch64_cortex-a72_musl')
logdir = root / 'logs/morse-2.2/audit-2026-11-02'
logdir.mkdir(parents=True, exist_ok=True)
(logdir / 'diagnostic-build-command.txt').write_text(shlex.join(args) + '\n')
with (logdir / 'diagnostic-build.log').open('w') as log:
    subprocess.run(args, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
module = source / 'morse.ko'
print('Compiled:', module)
print('SHA256:', hashlib.sha256(module.read_bytes()).hexdigest())
