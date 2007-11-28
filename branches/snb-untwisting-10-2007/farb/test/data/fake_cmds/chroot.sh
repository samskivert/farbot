#!/bin/sh
# Fake chroot(8) for testing purposes
# Just echo the command line arguments

echo $0 $*

# If the command to run in the chroot is make, take its last argument and 
# prepend the chroot directory to it, then run make with the full path.
if [ $2 = '/usr/bin/make' ] ; then
    chroot=$1
    dir=$4
    /usr/bin/make -C $chroot$dir

# Otherwise just shift off the chroot directory and execute the command
else
    shift
    $*
fi
