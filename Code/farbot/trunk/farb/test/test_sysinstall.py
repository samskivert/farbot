# test_sysinstall.py vi:ts=4:sw=4:expandtab:
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
from cStringIO import StringIO

from twisted.trial import unittest

import farb
from farb import sysinstall

# Useful Constants
from farb.test import DATA_DIR
from farb.test.test_config import RELEASE_CONFIG_FILE, RELEASE_CONFIG_FILE_IN
from farb.test.test_config import CONFIG_SUBS, rewrite_config

class MockConfigSection(sysinstall.ConfigSection):
    sectionOptions = [
        'optionA',
        'optionB',
        'optionC',
    ]

class ConfigSectionTestCase(unittest.TestCase):
    def test_serializeOptions(self):
        output = StringIO()
        cs = MockConfigSection()
        cs.optionA = 'A'

        cs._serializeOptions(output)
        self.assertEquals(output.getvalue(), 'optionA=A\n')

class ConfigTestCase(object):
    """ Mix-in class handles configuration file parsing and clean up """
    def setUp(self):
        # Load ZConfig schema
        self.schema = ZConfig.loadSchema(farb.CONFIG_SCHEMA)
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, CONFIG_SUBS)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        self.instSection = self.config.Installations.Installation[0]

    def tearDown(self):
        os.unlink(RELEASE_CONFIG_FILE)


class NetworkConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a NetworkConfig
        """
        nc = sysinstall.NetworkConfig(self.instSection, self.config)
        self.assertEquals(nc.nfshost, self.config.Releases.nfshost)

    def test_serialize(self):
        """
        Serialize a NetworkConfig
        """
        output = StringIO()
        instSect = self.instSection
        nc = sysinstall.NetworkConfig(self.instSection, self.config)
        # Do some basic validation of the serialized output
        expectedOutput = 'hostname=%s\ndomainname=%s\nnetdev=%s\nnfs=%s\ntryDHCP=YES\nmediaSetNFS\n' % (
                instSect.hostname,
                instSect.domain,
                instSect.networkdevice,
                nc.nfs
        )
        nc.serialize(output)
        self.assertEquals(output.getvalue(), expectedOutput)

class DistSetConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a DistSetConfig
        """
        dsc = sysinstall.DistSetConfig(self.instSection, self.config)

    def test_serialize(self):
        """
        Serialize a DistSetConfig
        """
        output = StringIO()
        instSect = self.instSection
        dsc = sysinstall.DistSetConfig(self.instSection, self.config)
        # Do some basic validation of the serialized output
        expectedOutput = 'dists=%s\ndistSetCustom\n' % (dsc.dists)
        dsc.serialize(output)
        self.assertEquals(output.getvalue(), expectedOutput)


class DiskLabelConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a DiskLabelConfig (Handles FreeBSD partitions)
        """
        dlc = sysinstall.DiskLabelConfig(self.config.Partitions.PartitionMap[0], 'ad0s1')

    def test_serialize(self):
        """
        Serialize a DiskPartitionConfig
        """
        output = StringIO()
        dlc = sysinstall.DiskLabelConfig(self.config.Partitions.PartitionMap[0], 'ad0s1')
        # Do some basic validation of the serialized output
        expectedOutput = 'ad0s1-1=%s\nad0s1-2=%s\nad0s1-3=%s\nad0s1-4=%s\nad0s1-5=%s\ndiskLabelEditor\n' % (
                getattr(dlc, 'ad0s1-1'),
                getattr(dlc, 'ad0s1-2'),
                getattr(dlc, 'ad0s1-3'),
                getattr(dlc, 'ad0s1-4'),
                getattr(dlc, 'ad0s1-5'),
        )
        dlc.serialize(output)
        self.assertEquals(output.getvalue(), expectedOutput)

class DiskPartitionConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a DiskPartitionConfig (Handles BIOS partitions)
        """
        dpc = sysinstall.DiskPartitionConfig(self.instSection.Disk[0], self.config)
        self.assertEquals(dpc.disk, 'ad0')

    def test_missingPartitionMap(self):
        """
        Intialize a DiskPartitionConfig with a missing PartitionMap
        """
        # Break referential integrity
        subs = CONFIG_SUBS.copy()
        subs['@PMAP@'] = 'DoesNotExist'

        # Rewrite and reload config
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        self.instSection = self.config.Installations.Installation[0]

        # Kaboom?
        self.assertRaises(sysinstall.ConfigError, sysinstall.DiskPartitionConfig, self.instSection.Disk[0], self.config)

    def test_serialize(self):
        """
        Serialize a DiskPartitionConfig
        """
        output = StringIO()
        dsc = sysinstall.DiskPartitionConfig(self.instSection.Disk[0], self.config)
        # Do some basic validation of the serialized output
        expectedOutput = 'disk=%s\npartition=%s\nbootManager=%s\ndiskPartitionEditor\n' % (
                dsc.disk,
                dsc.partition,
                dsc.bootManager
        )
        dsc.serialize(output)
        # Ensure that the partitionmap was serialized, and then cut it off.
        # ... this stuff is such a pain to test robustly.
        self.assert_(output.tell() > len(expectedOutput))
        output.truncate(len(expectedOutput))

        self.assertEquals(output.getvalue(), expectedOutput)

class PackageConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a PackageConfig
        """
        # Grab the first package from the first package set
        package = self.config.PackageSets.PackageSet[0].Package[0]
        pkgc = sysinstall.PackageConfig(package)
        self.assertEquals(pkgc.package, self.config.PackageSets.PackageSet[0].Package[0].package)

    def test_serialize(self):
        output = StringIO()
        package = self.config.PackageSets.PackageSet[0].Package[0]
        pkgc = sysinstall.PackageConfig(package)
        pkgc.serialize(output)
        self.assertEquals(output.getvalue(), 'package=%s\npackageAdd\n' % (package.package))

class InstallationConfigTestCase(ConfigTestCase, unittest.TestCase):
    def setUp(self):
        ConfigTestCase.setUp(self)
        self.inst = sysinstall.InstallationConfig(self.instSection, self.config)

    def test_init(self):
        """
        Initialize an InstallationConfig
        """
        self.assertEquals(self.inst.name, self.instSection.getSectionName())

    def test_missingPackageSet(self):
        """
        Intialize an InstallationConfig with a missing PackageSet
        """
        # Break referential integrity
        subs = CONFIG_SUBS.copy()
        subs['@PSET@'] = 'DoesNotExist'

        # Rewrite and reload config
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, subs)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        self.instSection = self.config.Installations.Installation[0]

        # Kaboom?
        self.assertRaises(sysinstall.ConfigError, sysinstall.InstallationConfig, self.instSection, self.config)

    def test_serialize(self):
        """
        Serialize an InstallationConfig
        """
        output = StringIO()
        self.inst.serialize(output)
        # No sane way to test this. Let's just see if it output anything.
        self.assert_(output.tell())
        print output.getvalue()
