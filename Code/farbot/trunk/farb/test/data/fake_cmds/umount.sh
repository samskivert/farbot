#!/bin/sh
# Fake umount(8) for testing purposes

# We support:
#    umount <mountpoint>

mountpoint=$1

# Validate that mountpoint is set 
if [ -z "$mountpoint" ]; then
    echo "Mountpoint is required"
    exit 1
fi

# Looks good 
exit 0
