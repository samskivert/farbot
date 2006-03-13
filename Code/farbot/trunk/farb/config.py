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

    # Global tftproot
    section.tftproot = os.path.join(section.installroot, 'tftproot')

    # Validate release sections and instantiate
    # ReleaseBuilders.
    for release in section.Release:
        if (tags.count(release.cvstag) > 0):
            raise ZConfig.ConfigurationError("CVS Tags may not be re-used in mutiple Release sections. (Tag: \"%s\")" % (release.cvstag))
        else:
            tags.append(release.cvstag)

        # The buildroot directory is merely a combination of the buildroot + release name
        release.buildroot = os.path.join(section.buildroot, release.getSectionName())
        # And the chroot
        release.chroot = os.path.join(release.buildroot, 'chroot')
        # And the ports tree
        release.portsdir = os.path.join(release.chroot, 'usr', 'ports')
        # And the package dir ...
        release.packagedir = os.path.join(release.portsdir, 'packages')

    return section

def release_handler(section):
    # Add an NULL packages attribute
    section.packages = None

    return section

def partition_handler(section):
    """
    Validate a partition map, performing appropriate datatype conversions
    where necessary.
    """

    # Validate known file systems
    if (section.type != 'ufs'):
        if (section.softupdates):
            # Only UFS supports softupdates. We'll fix this foible
            section.softupdates = False

    # If no mount point is specified, set string to "none"
    if (not section.mount):
        section.mount = 'none'

    # Convert bytes to 512 byte blocks
    section.size = section.size / 512

    return section

def package_handler(section):
    """
    Provide a reasonable default for the package name
    """
    if (not section.package):
        section.package = os.path.basename(section.port)

    return section

def verifyReferences(config):
    """
    Verify referential integrity between sections
    """
    for inst in config.Installations.Installation:
        # Verify that Disk's defined PartitionMaps exist
        for disk in inst.Disk:
            foundPartitionMap = False
            for map in config.Partitions.PartitionMap:
                if (disk.partitionmap.lower() == map.getSectionName()):
                    foundPartitionMap = True
                    break
            if (not foundPartitionMap):
                raise ZConfig.ConfigurationError, "Can't find partition map \"%s\" for disk \"%s\" in \"%s\" installation." % (disk.partitionmap, disk.getSectionName(), inst.getSectionName())

        # Verify that Installation's defined PackageSets exist
        for pkgsetName in inst.packageset:
            foundPackageSet = False
            for pkgset in config.PackageSets.PackageSet:
                if (pkgsetName.lower() == pkgset.getSectionName()):
                    foundPackageSet = True
                    break

            if (not foundPackageSet):
                raise ZConfig.ConfigurationError, "Can't find package set \"%s\" for \"%s\" installation." % (pkgsetName, inst.getSectionName())


def verifyPackages(config):
    """
    Verify a given installation has only unique packages defined
    for each release. Build a list of packages to be built for each
    release.
    @param config: ZConfig object containing farb configuration
    """

    # dictionary mapping packages to releases
    release_packages = {}

    # Iterate over installations, finding all packages in all package sets,
    # and then attaching that list to the release section.
    #
    # Additionally, verify that packages only appear *once* in 
    # all package sets used in a specified release.
    for install in config.Installations.Installation:
        releaseName = install.release.lower()
        release_packages[releaseName] = []
        for pkgsetName in install.packageset:
            for pkgset in config.PackageSets.PackageSet:
                if (pkgsetName.lower() == pkgset.getSectionName()):
                    for pkg in pkgset.Package:
                        # If if this package has already been listed
                        # by another packageset, in another installation,
                        # using the same release, throw an error
                        if (_hasPackage(release_packages, releaseName, pkg)):
                            raise ZConfig.ConfigurationError("Packages may not be listed in more than one package set within the same release. (Port: \"%s\", Package Set: \"%s\", Release: \"%s\")" % (pkg.port, pkgsetName, install.release))
                        else:
                            release_packages[releaseName].append(pkg)

    # Now add the package lists to the releases
    for release in config.Releases.Release:
        releaseName = release.getSectionName()
        # Do any installations reference this release?
        if (release_packages.has_key(releaseName)):
            # Don't add an empty list, leave release.packages set to None
            if (len(release_packages[releaseName])):
                release.packages = release_packages[releaseName]

def _hasPackage(release_packages, releaseName, newpkg):
    """
    Determine if a given package has already been added
    to the packages dictionary for a specified release.
    """
    for pkg in release_packages[releaseName]:
        if (pkg.port == newpkg.port): 
            return True

    return False
