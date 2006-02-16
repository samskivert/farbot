# test_builder.py vi:ts=4:sw=4:expandtab:
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

""" Builder Unit Tests """

import os

from twisted.trial import unittest
from twisted.internet import reactor, defer

from farb import builder

# Useful Constants
from farb.test import DATA_DIR

FREEBSD_SRC = os.path.join(DATA_DIR, 'buildtest')
MAKE_OUTPUT = os.path.join(FREEBSD_SRC, 'make.out')
MAKE_LOG = os.path.join(FREEBSD_SRC, 'make.log')
BUILDROOT = os.path.join(DATA_DIR, 'buildtest')
CVSROOT = '/cvs'
CVSTAG = 'tag'

# Reach in and tweak the FREEBSD_SRC constant
builder.FREEBSD_SRC = FREEBSD_SRC

class MakeProcessProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.log = file(MAKE_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(MAKE_LOG)

    def _makeResult(self, result):
        self.assertEquals(result, 0)
        self.log.seek(0)
        self.assertEquals('MakeProcessProtocol\n', self.log.read())

    def test_spawnProcess(self):
        d = defer.Deferred()
        pp = builder.MakeProcessProtocol(d, self.log)
        d.addCallback(self._makeResult)

        reactor.spawnProcess(pp, builder.MAKE_PATH, [builder.MAKE_PATH, '-C', BUILDROOT, 'protocol'])
        return d

class ReleaseBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.builder = builder.ReleaseBuilder(CVSROOT, CVSTAG, BUILDROOT)

    def tearDown(self):
        pass
        #os.unlink(MAKE_OUTPUT)

    def test_build(self):
        self.builder.build()
