#!/bin/sh
# Fake chroot(8) for testing purposes
# Just echo the command line arguments

echo $0 $*

# shift off the chroot directory and execute the command
shift
$*
