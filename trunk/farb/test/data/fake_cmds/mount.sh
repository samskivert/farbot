#!/bin/sh
# Fake mount(8) for testing purposes

# We support:
#    mount <device> <mountpoint>

type=

while getopts t: flag
do
    case $flag in
        t) type="$OPTARG" ;;
    esac
done

shift `expr $OPTIND - 1`
device=$1
mountpoint=$2

if [ -z '$3' ]; then
    echo "Extra arguments detected: $*"
    exit 1
fi

# Validate that both device and mountpoint are set 
if ! ([ ! -z "$device" ] && [ ! -z "$mountpoint" ]); then
    echo "Both device and mountpoint are required"
    exit 1
fi

# Echo Settings
echo $device
echo $mountpoint
if [ "x$type" != "x" ]; then
    echo $type
fi

# Looks good 
exit 0
