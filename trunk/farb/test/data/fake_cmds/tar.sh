#!/bin/sh
# Fake tar(1) for testing purposes. 

OS=`uname`
# Not every OS puts tar in /usr/bin like FreeBSD does. Hopefully it is at 
# least in the user's path.
REALTAR=`which tar`

# On FreeBSD we can execute tar with all the proper arguments.
if [ $OS = FreeBSD ]; then
    $REALTAR $*
else
# On other systems, the --unlink flag might not work properly (or at all), so 
# shift it off. It isn't needed in unit tests anyway.
    shift
    $REALTAR $*
fi
