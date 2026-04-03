#!/bin/sh

set -u

TTY_DEV="${TTY_DEV:-/dev/ttyS0}"
HCI_DEV="${HCI_DEV:-hci0}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOGFILE="${LOGFILE:-/tmp/bt-prime-attach-matrix.${STAMP}.log}"
TMPDIR="${TMPDIR:-/tmp/bt-prime-attach}"

mkdir -p "$TMPDIR"
: >"$LOGFILE"

log() {
	echo "$@" | tee -a "$LOGFILE"
}

run_cmd() {
	log "\$ $*"
	sh -c "$*" >>"$LOGFILE" 2>&1
}

cleanup_bt() {
	/etc/init.d/bluetoothd stop >/dev/null 2>&1 || true
	killall btattach hciattach >/dev/null 2>&1 || true
	hciconfig "$HCI_DEV" down >/dev/null 2>&1 || true
	sleep 1
}

prime_uart() {
	stty -F "$TTY_DEV" 115200 raw -echo >/dev/null 2>&1 || return 1
	printf 'W' >"$TTY_DEV"
	sleep 1
	return 0
}

bring_hci_up() {
	local i

	for i in $(seq 1 15); do
		if hciconfig "$HCI_DEV" up >/dev/null 2>&1; then
			return 0
		fi
		sleep 1
	done

	return 1
}

capture_state() {
	run_cmd "ps w | grep -E 'hciattach|btattach|bluetoothd' | grep -v grep || true"
	run_cmd "hciconfig -a || true"
	run_cmd "btmgmt info || true"
	run_cmd "dmesg | tail -n 20 || true"
}

run_variant() {
	local name="$1"
	local cmd="$2"
	local attach_log="$TMPDIR/${name}.log"

	log
	log "===== ${name} ====="
	cleanup_bt

	if ! prime_uart; then
		log "failed to prime ${TTY_DEV}"
		capture_state
		return
	fi

	: >"$attach_log"
	log "\$ $cmd"
	sh -c "$cmd" >"$attach_log" 2>&1 &
	ATTACH_PID=$!
	sleep 10

	if bring_hci_up; then
		log "hciconfig ${HCI_DEV} up: success"
	else
		log "hciconfig ${HCI_DEV} up: failed"
	fi

	run_cmd "cat '$attach_log'"
	capture_state

	kill "$ATTACH_PID" >/dev/null 2>&1 || true
	wait "$ATTACH_PID" >/dev/null 2>&1 || true
}

if [ ! -c "$TTY_DEV" ]; then
	echo "missing tty device: $TTY_DEV" >&2
	exit 1
fi

run_variant \
	"hciattach-bcm43xx-3000000-flow-primed" \
	"/usr/bin/hciattach -n -t 60 '$TTY_DEV' bcm43xx 3000000 flow"

run_variant \
	"hciattach-bcm43xx-921600-flow-primed" \
	"/usr/bin/hciattach -n -t 60 '$TTY_DEV' bcm43xx 921600 flow"

run_variant \
	"hciattach-bcm43xx-921600-noflow-primed" \
	"/usr/bin/hciattach -n -t 60 '$TTY_DEV' bcm43xx 921600 noflow"

run_variant \
	"hciattach-bcm43xx-3000000-noflow-primed" \
	"/usr/bin/hciattach -n -t 60 '$TTY_DEV' bcm43xx 3000000 noflow"

cleanup_bt
log
log "log saved to $LOGFILE"
