# config.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2006 Three Rings Design, Inc.
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

import os, ZConfig

import builder


def releases_handler(section):
    """
    Validate a group of defined releases.
    Instantiate corresponding ReleaseBuilder objects.
    """
    tags = []
    releases = []

    # Validate release sections and instantiate
    # ReleaseBuilders.
    for release in section.Release:
        if (tags.count(release.cvstag) > 0):
            raise ZConfig.ConfigurationError("CVS Tags may not be re-used in mutiple Release sections. (Tag: \"%s\")" % (release.cvstag))
        else:
            tags.append(release.cvstag)

    return section

def verifyPackages(config):
    """
    Verify a given installation has only unique packages defined
    for each release.
    @param config: ZConfig object containing farb configuration
    Returns a dictionary mapping releases to packages
    """

    # dictionary mapping packages to releases
    release_packages = {}
    for inst in config.Installations.Installation:
        releaseName = inst.release.lower()
        # insert a blank list when a new release is seen
        # so that .append() below will work
        if (not release_packages.has_key(releaseName)):
           release_packages[releaseName] = [] 
        for pset_name in inst.packageset:
            for pset in config.PackageSets.PackageSet:
                if (pset_name.lower() == pset.getSectionName()):
                    for p in pset.Package:
                        # if this release in this installation in this packageset
                        # has already listed this port then throw error
                        if (_hasPort(release_packages[releaseName], p.port)):
                            raise ZConfig.ConfigurationError("Ports may not be re-used in the same Installation sections. (Port: \"%s\")" % (p.port))
                        else:
                            release_packages[releaseName].append(p)
    return release_packages

def _hasPort(release_packages, port):
    """
    Determine if a given port is in a list of package sectionvalues 
    """
    for p in release_packages:
        if (p.port == port): 
            return 1 
    return 0
