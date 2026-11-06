#!/bin/sh
# Run on the OpenWrt node. Retain the beginning of boot, not a rotating tail.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root.' >&2; exit 1; }
[ -r /dev/kmsg ] && [ -x /sbin/procd ] || {
    echo 'This installer requires OpenWrt with /dev/kmsg.' >&2; exit 1;
}

mkdir -p /usr/libexec /usr/sbin
cat > /usr/libexec/morse22-early-reader <<'READER'
#!/bin/sh
umask 077
dir=/tmp/morse22-early
mkdir -p "$dir"
# Do not truncate the first capture if someone restarts the service.
[ ! -e "$dir/kernel.raw" ] || exit 0
cat /proc/sys/kernel/random/boot_id > "$dir/boot-id"
cat /proc/uptime > "$dir/recorder-start-uptime"
# Each read must accommodate a whole /dev/kmsg record. A separate reader
# does not consume logd's records. Keep the FIRST 16 MiB, never rotate.
dd if=/dev/kmsg bs=65536 2> "$dir/reader-errors.txt" |
    head -c 16777216 > "$dir/kernel.raw"
echo 'Reader exited; inspect reader-errors.txt and capture size.' > "$dir/reader-stopped.txt"
READER

cat > /etc/init.d/morse22-early <<'SERVICE'
#!/bin/sh /etc/rc.common
START=09
STOP=99
USE_PROCD=1
start_service() {
    procd_open_instance
    procd_set_param command /bin/sh /usr/libexec/morse22-early-reader
    # No respawn: preserve the first capture even if the size limit is hit.
    procd_close_instance
}
SERVICE

cat > /usr/sbin/morse22-collect <<'COLLECT'
#!/bin/sh
umask 077
dir=/tmp/morse22-early
[ -s "$dir/kernel.raw" ] || {
    echo 'No early capture found; check the morse22-early service.' >&2; exit 1;
}
{
    date
    uptime
    cat "$dir/boot-id" "$dir/recorder-start-uptime"
    ubus call system board
    opkg list-installed | grep -E '^(kmod-mm8108|mm8108-firmware|kmod-dot11ah) '
    sha256sum /lib/modules/"$(uname -r)"/morse.ko
    uci -q get gpsd.core.board
    ps w | grep '[g]pioset'
    lsusb
    lsusb -t
    iw dev
    iw dev wlh0 station dump
    batctl n
    wc -c "$dir/kernel.raw"
} > "$dir/status.txt" 2>&1
dmesg > "$dir/dmesg-tail.txt"
logread > "$dir/logread-tail.txt"
# Snapshot the live file before archiving it; the recorder keeps running.
cp "$dir/kernel.raw" "$dir/kernel-snapshot.raw"
tar -czf - -C "$dir" boot-id recorder-start-uptime kernel-snapshot.raw \
    reader-errors.txt status.txt dmesg-tail.txt logread-tail.txt
COLLECT

chmod 755 /usr/libexec/morse22-early-reader /etc/init.d/morse22-early /usr/sbin/morse22-collect
/etc/init.d/morse22-early enable
touch /etc/sysupgrade.conf
for path in /usr/libexec/morse22-early-reader /usr/sbin/morse22-collect \
    /etc/init.d/morse22-early /etc/rc.d/S09morse22-early /etc/rc.d/K99morse22-early; do
    grep -qxF "$path" /etc/sysupgrade.conf || echo "$path" >> /etc/sysupgrade.conf
done
/etc/init.d/morse22-early start
echo 'Installed. Reboot normally first, then collect the baseline before upgrading.'
echo 'Captures live in RAM: download them before rebooting or removing power.'
