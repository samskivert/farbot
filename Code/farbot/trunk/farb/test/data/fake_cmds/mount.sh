#!/bin/sh
# Fake mount(8) for testing purposes

# We support:
#    mount <device> <mountpoint>

device=$1
mountpoint=$2

# Validate that both device and mountpoint are set 
if ! ([ ! -z "$device" ] && [ ! -z "$mountpoint" ]); then
    echo "Both device and mountpoint are required"
    exit 1
fi

# Looks good 
exit 0
