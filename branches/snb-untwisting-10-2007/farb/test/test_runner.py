# test_runner.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2007 Three Rings Design, Inc.
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

""" Runner Unit Tests """

import os
import shutil
import unittest
import ZConfig

import farb
from farb import config, runner, utils

# Useful Constants
from farb.test import rewrite_config
from farb.test.test_builder import BUILDROOT, CDROM_INF, CDROM_INF_IN, ISO_MOUNTPOINT, builder
from farb.test.test_config import RELEASE_CONFIG_FILE, RELEASE_CONFIG_FILE_IN, CONFIG_SUBS

SCHEMA = ZConfig.loadSchema(farb.CONFIG_SCHEMA)
RELEASE_NAMES = ['6.0', '6.2-release']
DISTFILES_CACHE = os.path.join(BUILDROOT, 'distfiles')

class ReleaseBuildRunnerTestCase(unittest.TestCase):
    def setUp(self):
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, CONFIG_SUBS)
        farbconfig, handler = ZConfig.loadConfig(SCHEMA, RELEASE_CONFIG_FILE)
        self.rbr = runner.ReleaseBuildRunner(farbconfig)
        self.rbr.run()
    
    def tearDown(self):
        os.unlink(RELEASE_CONFIG_FILE)
        for release in RELEASE_NAMES:
            releaseroot = os.path.join(BUILDROOT, release)
            shutil.rmtree(releaseroot)
    
    def test_runTwice(self):
        """ 
        Test doing one release build after another without removing buildroot 
        between builds
        """
        self.rbr.run()
    
    def test_buildLogs(self):
        """ Test that build logs are created for each valid release """
        for name in RELEASE_NAMES:
            self.assertTrue(os.path.exists(os.path.join(BUILDROOT, name, 'build.log')))
    
    def test_skippedRelease(self):
        """ 
        Test that a release without a corresponding installation is not built 
        """
        self.assertFalse(os.path.exists(os.path.join(BUILDROOT, '6-stable')))
    
    def test_binaryRelease(self):
        """ 
        Test that the directory structure for a copied CD is created when using 
        a binary release
        """
        self.assertTrue(os.path.exists(os.path.join(BUILDROOT, '6.2-release', 'releaseroot', builder.RELEASE_CD_PATH)))

class PackageBuildRunnerTestCase(unittest.TestCase):
    def setUp(self):
        rewrite_config(RELEASE_CONFIG_FILE_IN, RELEASE_CONFIG_FILE, CONFIG_SUBS)
        farbconfig, handler = ZConfig.loadConfig(SCHEMA, RELEASE_CONFIG_FILE)
        config.verifyPackages(farbconfig)
        # Copy in each release needed
        for release in RELEASE_NAMES:
            rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = ' + release.upper()})
            dest = os.path.join(BUILDROOT, release, 'releaseroot', builder.RELEASE_CD_PATH)
            utils.copyRecursive(ISO_MOUNTPOINT, dest)
            # The fake CD image we have is for 6.2, so we might need to rename a 
            # directory
            os.rename(os.path.join(dest, '6.2-RELEASE'), os.path.join(dest, release.upper()))
        
        self.pbr = runner.PackageBuildRunner(farbconfig)
        self.pbr.run()
    
    def tearDown(self):
        os.unlink(RELEASE_CONFIG_FILE)
        for release in RELEASE_NAMES:
            releaseroot = os.path.join(BUILDROOT, release)
            if os.path.exists(releaseroot):
                shutil.rmtree(releaseroot)
        if os.path.exists(DISTFILES_CACHE):
            os.rmdir(DISTFILES_CACHE)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)
    
    def test_runTwice(self):
        """ 
        Test doing one package build after another without removing buildroot 
        between builds
        """
        self.pbr.run()

    def test_packageLogs(self):
        """ Test that package build logs are created for each valid release """
        for name in RELEASE_NAMES:
            self.assertTrue(os.path.exists(os.path.join(BUILDROOT, name, 'packaging.log')))
    
    def test_portFetchMethods(self):
        """ Test that ports are fetched appropriately with CVS or portsnap """
        sudoPort = os.path.join('pkgroot', 'usr', 'ports', 'security', 'sudo')
        mysqlPort = os.path.join('pkgroot', 'usr', 'ports', 'databases', 'mysql50-server')
        self.assertTrue(os.path.exists(os.path.join(BUILDROOT, '6.0', sudoPort)))
        self.assertTrue(os.path.exists(os.path.join(BUILDROOT, '6.2-release', sudoPort)))
        self.assertTrue(os.path.exists(os.path.join(BUILDROOT, '6.0', mysqlPort)))
        self.assertFalse(os.path.exists(os.path.join(BUILDROOT, '6.2-release', mysqlPort)))
    
class NetInstallAssemblerRunnerTestCase(unittest.TestCase):
    pass
