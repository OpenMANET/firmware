#!/bin/sh
#
# Copyright (C) 2023 MorseMicro
#


operation="$1"
key="$2"
value="$3"

set -eu

get_key_from_persistent_storage()
{
    local config_key=
    config_key=$(vcgencmd bootloader_config | grep "$key=")
    config_key=$(echo "$config_key" | sed "s/$key=//g")
    echo "$config_key"
}

print_usage()
{
    echo "persistent_vars_storage.sh OPERATION(READ|READALL|WRITE|ERASE) KEY [VALUE]" 1>&2;
}

all_keys="device_password default_wifi_key dpp_priv_key mm_region
    mm_virtual_wire mm_mode dropbear_authorized_keys dropbear_ed25519_host_key
    dropbear_rsa_host_key"

case "$operation" in
    READ)
        value=$(get_key_from_persistent_storage)
        if [ -n "$value" ]; then
            echo "$value"
            exit 0
        else
            echo "The key \"$key\" doesn't exist in bootloader config." 1>&2;
            print_usage
            exit 1
        fi
    ;;

    READALL)
        for key in $all_keys; do
            printf '%s=%s\n' "$key" "$($0 READ "$key")"
        done
    ;;

    WRITE|ERASE)
        echo "Writing to persistent memory isn't implemented on bcm2712, yet." 1>&2;
        exit 1
    ;;

    *)
        print_usage
        exit 1
    ;;

esac
