#!/bin/sh
# Fake mdconfig(1) for testing purposes

# We support:
#    mdconfig -a -t vnode -f <file>
#    mdconfig -d -u <unit>

aflag=
dflag=

type=
unit=
file=

while getopts adt:u:f: flag
do
    case $flag in
        a) aflag=1 ;;
        d) dflag=1 ;;
        t) type="$OPTARG" ;;
        u) unit="$OPTARG" ;;
        f) file="$OPTARG" ;;
    esac
done

# Validate that either -a or -d was specified
if [ ! -z "$aflag" ] && [ ! -z "$dflag" ]; then
    echo "Can not specify both -a and -d"
    exit 1
fi

if [ -z "$aflag" ] && [ -z "$dflag" ]; then
    echo "Must specify one of -a or -d"
    exit 1
fi

# If -a, validate other options
if [ ! -z "$aflag" ]; then
    if [ -z "$type" ] || [ -z "$file" ]; then
        echo "Must specify both -t <type> and -f <file>"
        exit 1
    fi
    if [ "$type" != "vnode" ]; then
        echo "Only -t vnode is supported"
        exit 1
    fi

    # Return a fake device name
    echo "md0"
    exit 0
fi

# If -d, validate other options
if [ ! -z "$dflag" ]; then
    if [ -z "$unit" ]; then
        echo "Must specify -u <unit>"
        exit 1
    fi
    if [ "$unit" != "md0" ]; then
        echo "What are you doing? We only ever return 'md0'"
        exit 1
    fi

    exit 0
fi

# Never reached
exit 1
