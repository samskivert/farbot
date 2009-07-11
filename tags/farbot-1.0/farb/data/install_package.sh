#!/bin/sh
# install_package.sh vi:ts=4:sw=4:expandtab:
# Handle installation of packages so that sysinstall doesn't have to.
#
# Copyright (c) 2006-2008 Three Rings Design, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright owner nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Prevent pkg_add from trying to interact with the user
export PACKAGE_BUILDING=1
export BATCH=1
# Look for packages on the installation media
export PKG_PATH="/dist/packages/Latest:/dist/packages/All"


# Print Usage
usage() {
    echo "$0 <package>"
}

# Install the package
installPackage() {
    pkg="$1"
    # Exit cleanly if the package is already installed

    # Glob to check
    glob='*pkg_add: package * or its older version already installed*'

    echo "Installing $pkg ..."
    # Install the package
    msg=`pkg_add $pkg 2>&1`
    # Test result
    if [ "$?" = "1" ]; then
        case "$msg" in
            $glob)
                echo "$pkg is already installed (perhaps by a dependency) ..."
                exit 0
                ;;
            *)
                echo "$msg"
                exit 1
                ;;
        esac
    fi

    echo "$msg"
}

main() {
    pkg=$1
    if [ -z "$pkg" ]; then
        usage
        exit 1
    fi

    # Do it!
    installPackage $pkg
}

main $1
