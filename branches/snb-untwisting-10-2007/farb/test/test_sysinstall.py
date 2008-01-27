# test_sysinstall.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2006-2007 Three Rings Design, Inc.
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
import string
import unittest

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

    sectionCommands = [
        'commandA'
    ]

    otherCommands = [
        'commandB'
    ]

class ConfigSectionTestCase(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.cs = MockConfigSection()
        self.cs.optionA = 'A'

    def test_serializeOptions(self):
        """
        Test ConfigSection serializing Options
        """
        self.cs._serializeOptions(self.output)
        self.assertEquals(self.output.getvalue(), 'optionA=A\n')

    def test_serializeSectionCommands(self):
        """
        Test ConfigSection serializing Commands
        """
        self.cs._serializeCommands(self.output)
        self.assertEquals(self.output.getvalue(), 'commandA\n')

    def test_serializeOtherCommands(self):
        """
        Test ConfigSection serializing OtherCommands
        """
        self.cs._serializeCommands(self.output, commands=self.cs.otherCommands)
        self.assertEquals(self.output.getvalue(), 'commandB\n')


class ConfigTestCase(object):
    """ Mix-in class handles configuration file parsing and clean up """
    def setUp(self):
        # Load ZConfig schema
        self.schema = ZConfig.loadSchema(farb.CONFIG_SCHEMA)
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, CONFIG_SUBS)
        self.config, handler = ZConfig.loadConfig(self.schema, RELEASE_CONFIG_FILE)
        self.instSection = self.config.Installations.Installation[0]
        self.releaseSection = self.config.Releases.Release[0]
        self.instSectionNoCommands = self.config.Installations.Installation[1]
        self.instSectionNoDisks = self.config.Installations.Installation[2]

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
        expectedOutput = 'hostname=%s\ndomainname=%s\nnetDev=%s\nnfs=%s\ntryDHCP=YES\nmediaSetNFS\n' % (
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
        dsc = sysinstall.DistSetConfig(self.releaseSection, self.config)

    def test_serialize(self):
        """
        Serialize a DistSetConfig
        """
        output = StringIO()
        instSect = self.instSection
        dsc = sysinstall.DistSetConfig(self.releaseSection, self.config)
        # Do some basic validation of the serialized output
        expectedOutput = 'dists=%s\ndistSetCustom\n' % ("src szomg swtf base")
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
        """
        Serialize an PackageConfig 
        """
        output = StringIO()
        package = self.config.PackageSets.PackageSet[0].Package[0]
        pkgc = sysinstall.PackageConfig(package)
        pkgc.serialize(output)
        self.assertEquals(output.getvalue(), 'command=/dist/install_package.sh %s\nsystem\n' % (package.package))

class SystemCommandConfigTestCase(ConfigTestCase, unittest.TestCase):
    def test_init(self):
        """
        Initialize a SystemCommandConfig
        """
        # Grab the first system command 
        cmd = self.config.Installations.Installation[0].PostInstall.command[0]
        scc = sysinstall.SystemCommandConfig(cmd)
        self.assertEquals(scc.cmd, '/dist/local/cleanup.sh everything')

    def test_serialize(self):
        """
        Serialize an SystemCommandConfig 
        """
        output = StringIO()
        cmd = self.config.Installations.Installation[0].PostInstall.command[0]
        scc = sysinstall.SystemCommandConfig(cmd)
        scc.serialize(output)
        self.assertEquals(output.getvalue(), 'command=/dist/local/cleanup.sh everything\nsystem\n')

class InstallationConfigTestCase(ConfigTestCase, unittest.TestCase):
    def setUp(self):
        ConfigTestCase.setUp(self)
        self.inst = sysinstall.InstallationConfig(self.instSection, self.config)

    def test_init(self):
        """
        Initialize an InstallationConfig
        """
        self.assertEquals(self.inst.name, self.instSection.getSectionName())

    def test_noCommands(self):
        """
        Test for no post-installation command handling.
        See: https://dpw.threerings.net/pipermail/farbot/2006-November/000033.html
        """
        inst = sysinstall.InstallationConfig(self.instSectionNoCommands, self.config)
        
    def test_noDisks(self):
        """
        Test installations where no disks are defined. 
        """
        inst = sysinstall.InstallationConfig(self.instSectionNoDisks, self.config)
        output = StringIO()
        # Verify that the expected disk related stuff is in the serialized output
        expectedOutput = 'diskInteractive="YES"\ndiskPartitionEditor\ndiskLabelEditor'
        inst.serialize(output)
        assert(string.find(output.getvalue(), expectedOutput) >= 0)

    def test_serialize(self):
        """
        Serialize an InstallationConfig
        """
        output = StringIO()
        self.inst.serialize(output)
        # No sane way to test this. Let's just see if it output anything.
        self.assert_(output.tell())
