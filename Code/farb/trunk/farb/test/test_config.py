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
from farb.test import DATA_DIR
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
    '@TAG2@' : 'RELENG_6'
}

def rewrite_config(inpath, outpath, variables):
        # Fix up paths in the farb configuration file
        output = open(outpath, 'w')
        input = open(inpath, 'r')
        for line in input:
            for key,value in variables.iteritems():
                line = line.replace(key, value)
            output.write(line)

        output.close()
        input.close()


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
        self.assertEquals(config.Releases.Release[0].buildroot, os.path.join(BUILDROOT, '6.0'))
        
    def test_package_sets(self):
        """ Load a standard package set configuration """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        self.assertEquals(config.PackageSets.PackageSet[0].Package[0].port, 'security/sudo')

    def test_release_packages(self):
        """ Test release_packages dictionary contains good values """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        release_packages = farb.config.verifyPackages(config)
        self.assertEquals(release_packages['6-STABLE'][0].port, 'security/sudo')

    def test_packages_unique(self):
        """ Test handling of duplicate packages in a good package set """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_CONFIG_FILE)
        farb.config.verifyPackages(config)

    def test_packages_uniqueFailure(self):
        """ Test handling of duplicate packages in a bad package set """
        config, handler = ZConfig.loadConfig(self.schema, PACKAGES_BAD_CONFIG_FILE)
        self.assertRaises(ZConfig.ConfigurationError, farb.config.verifyPackages, config)
