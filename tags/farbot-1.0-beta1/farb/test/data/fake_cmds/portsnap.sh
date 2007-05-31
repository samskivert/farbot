#!/bin/sh
# Fake portsnap(8) for testing purposes

# We support:
#    portsnap [-p portsdir] <command>

portsdir=

while getopts p: flag
do
    case $flag in
        p) portsdir="$OPTARG" ;;
    esac
done

shift `expr $OPTIND - 1`
command=$1

if [ -z '$2' ]; then
    echo "Extra arguments detected: $*"
    exit 1
fi

# Validate that command is either extract or fetch
if ! ([ $command = "fetch" -o $command = "extract" ]); then
    echo "Command must be either fetch or extract"
    exit 2
fi

# Echo Settings
echo $command
if [ "x$portsdir" != "x" ]; then
    echo $portsdir
fi

# Looks good 
exit 0
