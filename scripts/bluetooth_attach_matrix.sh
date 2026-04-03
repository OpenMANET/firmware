#!/bin/sh

set -u

TTY_DEV="${TTY_DEV:-/dev/ttyS0}"
HCI_DEV="${HCI_DEV:-hci0}"
SLEEP_SECS="${SLEEP_SECS:-10}"
OUT="${OUT:-/tmp/bluetooth-attach-matrix.$(date +%Y%m%d-%H%M%S).log}"

log() {
	printf '%s\n' "$*" | tee -a "$OUT"
}

run_capture() {
	label="$1"
	cmd="$2"

	log ""
	log "===== $label ====="
	log "CMD: $cmd"

	/etc/init.d/bluetoothd stop >/dev/null 2>&1 || true
	killall btattach hciattach >/dev/null 2>&1 || true
	hciconfig "$HCI_DEV" down >/dev/null 2>&1 || true
	rm -f /tmp/hciattach.log /tmp/btattach.log

	sh -c "$cmd" >/tmp/bt-test.log 2>&1 &
	pid=$!

	sleep "$SLEEP_SECS"

	log "--- ps ---"
	ps w | grep -E "btattach|hciattach" | grep -v grep | tee -a "$OUT"

	log "--- tool log ---"
	cat /tmp/bt-test.log 2>/dev/null | tee -a "$OUT"

	log "--- hciconfig -a ---"
	hciconfig -a 2>&1 | tee -a "$OUT"

	log "--- btmgmt info ---"
	btmgmt info 2>&1 | tee -a "$OUT"

	log "--- dmesg tail -n 10 ---"
	dmesg | tail -n 10 | tee -a "$OUT"

	kill "$pid" >/dev/null 2>&1 || true
	killall btattach hciattach >/dev/null 2>&1 || true
	hciconfig "$HCI_DEV" down >/dev/null 2>&1 || true
}

log "Writing results to $OUT"
log "TTY_DEV=$TTY_DEV HCI_DEV=$HCI_DEV SLEEP_SECS=$SLEEP_SECS"

run_capture \
	"btattach bcm 3000000 noflow" \
	"/usr/bin/btattach -B $TTY_DEV -P bcm -S 3000000 -N"

run_capture \
	"hciattach bcm43xx 3000000 flow" \
	"/usr/bin/hciattach -n -t 60 $TTY_DEV bcm43xx 3000000 flow"

run_capture \
	"hciattach bcm43xx 3000000 noflow" \
	"/usr/bin/hciattach -n -t 60 $TTY_DEV bcm43xx 3000000 noflow"

run_capture \
	"hciattach bcm43xx 921600 noflow" \
	"/usr/bin/hciattach -n -t 60 $TTY_DEV bcm43xx 921600 noflow"

run_capture \
	"hciattach bcm43xx 115200 noflow" \
	"/usr/bin/hciattach -n -t 60 $TTY_DEV bcm43xx 115200 noflow"

run_capture \
	"hciattach bcm43xx-3wire 921600 noflow" \
	"/usr/bin/hciattach -n -t 60 $TTY_DEV bcm43xx-3wire 921600 noflow"

log ""
log "Done. Full log: $OUT"
