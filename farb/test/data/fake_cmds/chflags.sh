#!/bin/sh
# Fake chflags(1) for testing purposes

# We support:
#    chflags -R 0 /some/path

if [ $# -lt 3 ]; then
    echo "Not enough arguments"
    exit 1
fi

Rflag=

while getopts R flag
do
    case $flag in
        R) Rflag=1 ;;
    esac
done

shift `expr $OPTIND - 1`
file_flag=$1
path=$2

if [ $Rflag -ne 1 ]; then
    echo "-R flag was not given"
    exit 2
fi

if [ $file_flag -ne 0 ]; then
    echo "Can not set flags other than 0 (none)"
    exit 3
fi

if [ -z $path ]; then
    echo "No path given"
    exit 4
fi

echo $path

# Looks good 
exit 0