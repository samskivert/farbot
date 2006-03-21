#!/bin/sh
# Fake pkg_delete(8) for testing purposes

# We support:
#    pkg_delete -a

aflag=

while getopts a flag
do
    case $flag in
        a) aflag='1' ;;
    esac
done

echo $*

# Looks good 
exit 0
