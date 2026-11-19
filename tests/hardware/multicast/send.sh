#!/bin/sh
# Runs on the sending node. Keep capture and BATMAN state under one owner.
set -eu
dir=$1 mesh=$2 hardif=$3 bridge=$4 mode=$5 token=$6 seconds=$7 settle=$8
lock=/tmp/openmanet-multicast-"$mesh".lock
mkdir "$lock" || { echo "Sender already locked: $lock" >&2; exit 1; }
original=
capture=
restore() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "$capture" ]; then
        kill -INT "$capture" 2>/dev/null || :
        wait "$capture" || status=1
    fi
    if [ -n "$original" ]; then
        batctl meshif "$mesh" multicast_mode "$original" &&
            [ "$(batctl meshif "$mesh" multicast_mode)" = "$original" ] || status=1
    fi
    rmdir "$lock" || status=1
    exit "$status"
}
trap restore EXIT
trap 'exit 1' HUP INT TERM
if [ "$mode" = raw ]; then
    exec_iface=$hardif
    filter='ether proto 0x88b5'
    protocol=raw
else
    state=$(batctl meshif "$mesh" multicast_mode)
    case "$state" in enabled|disabled) original=$state;; *) exit 1;; esac
    printf 'original multicast_mode=%s\n' "$original" >&2
    batctl meshif "$mesh" multicast_mode "$mode"
    [ "$(batctl meshif "$mesh" multicast_mode)" = "$mode" ]
    exec_iface=$bridge
    filter='ether proto 0x4305'
    protocol=udp
fi
# Allow listener announcements and forwarding changes to propagate.
sleep "$settle"
LC_ALL=C tcpdump -Q out -i "$hardif" -s 0 -w - "$filter" >"$dir/out.pcap" 2>"$dir/capture.log" &
capture=$!
i=0
until grep -q 'listening on' "$dir/capture.log"; do
    kill -0 "$capture" || { cat "$dir/capture.log" >&2; exit 1; }
    i=$((i + 1))
    [ "$i" -lt 5 ] || { cat "$dir/capture.log" >&2; exit 1; }
    sleep 1
done
"$dir/probe" send "$protocol" "$exec_iface" "$token" "$seconds" 60 50
sleep 1
