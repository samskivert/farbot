# test_config.py vi:ts=4:sw=4:expandtab:
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

""" Configuration Unit Tests """

import os
import ZConfig

from twisted.trial import unittest

import farb
from farb import config

# Useful Constants
from farb.test import DATA_DIR, rewrite_config
from farb.test.test_builder import CVSROOT, BUILDROOT

CONFIG_DIR = os.path.join(DATA_DIR, 'test_configs')

RELEASE_CONFIG_FILE = os.path.join(CONFIG_DIR, 'release.conf')
RELEASE_CONFIG_FILE_IN = RELEASE_CONFIG_FILE + '.in'

PACKAGES_CONFIG_FILE = os.path.join(CONFIG_DIR, 'packages.conf')
PACKAGES_CONFIG_FILE_IN = PACKAGES_CONFIG_FILE + '.in'
PACKAGES_BAD_CONFIG_FILE = os.path.join(CONFIG_DIR, 'packages-bad.conf')
PACKAGES_BAD_CONFIG_FILE_IN = PACKAGES_BAD_CONFIG_FILE + '.in'

CONFIG_SUBS = {
    '@CVSROOT@' : CVSROOT,
    '@BUILDROOT@' : BUILDROOT,
    '@TAG1@' : 'RELENG_6_0',
    '@TAG2@' : 'RELENG_6',
    '@SWAPSU@' : 'False',
    '@PMAP@' : 'Standard',
    '@PSET@' : 'Base',
    '@RELEASETYPE@' : 'BinaryRelease True',
    '@PORTSOURCE@' : 'UsePortsnap True',
    '@ISO@' : 'ISO ' + os.path.join(DATA_DIR, 'fake_cd.iso')
}

class ConfigParsingTestCase(unittest.TestCase):
    def setUp(self):
        # Load ZConfig schema
        self.schema = ZConfig.loadSchema(farb.CONFIG_SCHEMA)
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, CONFIG_SUBS)
        rewrite_config(PACKAGES_CONFIG_FILE_IN, PACKAGES_CONFIG_FILE, CONFIG_SUBS)
        rewrite_config(PACKAGES_BAD_CONFIG_FILE_IN, PACKAGES_BAD_CONFIG_FILE, CONFIG_SUBS)

    def tearDown(self):
        os.unlink(RELEASE_CONFIG_FILE)
        os.unlink(PACKAGES_CONFIG_FILE)
        os.unlink(PACKAGES_BAD_CONFIG_FILE)

    def test_releases_cvstag(self):
        """ Test handling of duplicate CVS Tags """
        bs = CONFIG_SUBS.copy()
        bs['@TAG1@'] = 'boom'
        bs['@TAG2@'] = 'boom'
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, bs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)

    def test_releases(self):
        """ Load a standard release configuration """
        config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        # Releases tftproot
        tftproot = os.path.join(config.Releases.installroot, 'tftproot')
        self.assertEquals(config.Releases.tftproot, tftproot)

        # Per-release settings
        release = config.Releases.Release[0]
        buildroot = os.path.join(config.Releases.buildroot, release.getSectionName())
        chroot = os.path.join(buildroot, 'chroot')
        portsdir = os.path.join(buildroot, 'usr', 'ports')
        packagedir = os.path.join(portsdir, 'packages')
        self.assertEquals(release.cvstag, 'RELENG_6_0')
        self.assertEquals(release.packages, None)
        self.assertEquals(release.buildroot, buildroot)
        self.assertEquals(release.chroot, chroot)
    
    def test_binary_release(self):
        """ Load a binary release configuration """
        config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        release = config.Releases.Release[2]
        # Make sure options were set correctly
        self.assertEquals(release.binaryrelease, True)
        self.assertEquals(release.useportsnap, True)
        self.assertEquals(release.iso, os.path.join(DATA_DIR, 'fake_cd.iso'))
        
    def test_missing_release_type(self):
        """ Test handling of unset release type """
        subs = CONFIG_SUBS.copy()
        del subs['@RELEASETYPE@']
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)
    
    def test_cvsroot_present(self):
        """ Verify CVSRoot is set when BinaryRelease is False """
        subs = CONFIG_SUBS.copy()
        subs['@RELEASETYPE@'] = 'CVSTag RELENG_6_0'
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)
    
    def test_cvstag_present(self):
        """ Verify CVSTag is set when BinaryRelease is False """
        subs = CONFIG_SUBS.copy()
        subs['@PORTSOURCE@'] = 'CVSRoot ' + CVSROOT
        subs['@RELEASETYPE@'] = 'BinaryRelease False'
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)
    
    def test_missing_iso(self):
        """ Test handling of BinaryReleases without ISO """
        subs = CONFIG_SUBS.copy()
        del subs['@ISO@']
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)

    def test_missing_ports_source(self):
        """ Test handling of UsePortsnap and CVSRoot not existing """
        subs = CONFIG_SUBS.copy()
        del subs['@PORTSOURCE@']
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.assertRaises(ZConfig.ConfigurationError, ZConfig.loadConfig, self.schema, RELEASE_CONFIG_FILE)

    def test_ports_cvs(self):
        """ Test using CVS for ports in binary release """
        subs = CONFIG_SUBS.copy()
        subs['@PORTSOURCE@'] = 'CVSRoot ' + CVSROOT
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        release = config.Releases.Release[2]
        self.assertEquals(release.cvsroot, CVSROOT)

    def test_partition_softupdates(self):
        """ Verify that SoftUpdates flags are tweaked appropriately """
        bs = CONFIG_SUBS.copy()
        bs['@SWAPSU@'] = 'True'
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, bs)

        config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        for part in config.Partitions.PartitionMap[0].Partition:
            if (part.type == 'swap'):
                self.assertEquals(part.softupdates, False)
            elif (part.mount == '/usr'):
                self.assertEquals(part.softupdates, True)

    def test_partition_softupdates(self):
        """ Verify that partition sizes are converted correctly """
        config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        for part in config.Partitions.PartitionMap[0].Partition:
            if (part.type == 'swap'):
                # The swap partition should be 4GB, or 8,388,608 512-byte blocks
                self.assertEquals(part.size, 8388608)

    def test_package_sets(self):
        """ Load a standard package set configuration """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        self.assertEquals(config.PackageSets.PackageSet[0].Package[0].port, 'security/sudo')
        self.assertEquals(config.PackageSets.PackageSet[1].Package[0].port, 'databases/mysql50-server')
        self.assertEquals(config.PackageSets.PackageSet[1].Package[0].BuildOptions.Options['WITH_COLLATION'], 'UTF8')

    def test_release_packages(self):
        """ Test that the release packages list contains good values """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        farb.config.verifyPackages(config)
        self.assertEquals(config.Releases.Release[1].packages[0].port, 'security/sudo')
        # Test default handling
        self.assertEquals(config.Releases.Release[1].packages[0].package, 'sudo')
        # Test default override
        self.assertEquals(config.Releases.Release[1].packages[1].package, 'overwrote')
        # Verify that all package sets are loaded
        self.assertEquals(config.Releases.Release[0].packages[2].package, 'mysql50-server')

    def test_packages_unique(self):
        """ Test handling of duplicate packages in a good package set """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        farb.config.verifyPackages(config)

    def test_packages_uniqueFailure(self):
        """ Test handling of duplicate packages in a bad package set """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_BAD_CONFIG_FILE)
        self.assertRaises(ZConfig.ConfigurationError, farb.config.verifyPackages, config)

    def test_missingPartitionMap(self):
        """
        Test handling of a missing PartitionMap
        """
        # Break referential integrity
        subs = CONFIG_SUBS.copy()
        subs['@PMAP@'] = 'DoesNotExist'

        # Rewrite and reload config
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)

        # Kaboom?
        self.assertRaises(ZConfig.ConfigurationError, config.verifyReferences, self.config)

    def test_missingPackageSet(self):
        """
        Test handling of a missing PackageSet
        """
        # Break referential integrity
        subs = CONFIG_SUBS.copy()
        subs['@PSET@'] = 'DoesNotExist'

        # Rewrite and reload config
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        self.instSection = self.config.Installations.Installation[0]

        # Kaboom?
        self.assertRaises(ZConfig.ConfigurationError, config.verifyReferences, self.config)
