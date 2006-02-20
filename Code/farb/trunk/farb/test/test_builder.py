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

FREEBSD_REL_PATH = os.path.join(DATA_DIR, 'buildtest')
MAKE_LOG = os.path.join(FREEBSD_REL_PATH, 'make.log')
MAKE_OUT = os.path.join(FREEBSD_REL_PATH, 'make.out')


BUILDROOT = os.path.join(DATA_DIR, 'buildtest')
CHROOT = os.path.join(BUILDROOT, 'chroot')
CVSROOT = os.path.join(DATA_DIR, 'fakencvs')
CVSTAG = 'RELENG_6_0'

# Reach in and tweak the FREEBSD_REL_PATH constant
builder.FREEBSD_REL_PATH = FREEBSD_REL_PATH

class MakeProcessProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(MAKE_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(MAKE_LOG)
        os.unlink(MAKE_OUT)

    def _makeResult(self, result):
        o = open(MAKE_OUT, 'r')
        self.assertEquals('MakeProcessProtocol\n', o.read())
        o.close()
        self.assertEquals(result, 0)

    def test_spawnProcess(self):
        d = defer.Deferred()
        pp = builder.MakeProcessProtocol(d, self.log)
        d.addCallback(self._makeResult)

        reactor.spawnProcess(pp, builder.MAKE_PATH, [builder.MAKE_PATH, '-C', BUILDROOT, 'protocol'])
        return d

    def _makeSuccess(self, result):
        self.fail("This call should not have succeeded")

    def _makeError(self, result):
        self.assertNotEqual(result, 0)

    def test_makeError(self):
        d = defer.Deferred()
        pp = builder.MakeProcessProtocol(d, self.log)
        d.addCallbacks(self._makeSuccess, self._makeError)

        reactor.spawnProcess(pp, builder.MAKE_PATH, [builder.MAKE_PATH, '-C', BUILDROOT, 'error'])
        return d

class MakeCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(MAKE_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(MAKE_LOG)
        os.unlink(MAKE_OUT)

    def _makeResult(self, result):
        o = open(MAKE_OUT, 'r')
        self.assertEquals('MakeCommand 1 2\n', o.read())
        o.close()
        self.assertEquals(result, 0)

    def test_make(self):
        makeOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }

        mc = builder.MakeCommand(BUILDROOT, 'makecommand', makeOptions)
        d = mc.make(self.log)
        d.addCallback(self._makeResult)

        return d

class NCVSBuildnameProcessProtocolTestCase(unittest.TestCase):
    def _cvsResult(self, result):
        self.assertEquals(result, '6.0-RELEASE-p4')

    def test_spawnProcess(self):
        d = defer.Deferred()
        pp = builder.NCVSBuildnameProcessProtocol(d)
        d.addCallback(self._cvsResult)

        reactor.spawnProcess(pp, builder.CVS_PATH, [builder.CVS_PATH, '-d', CVSROOT, 'co', '-p', '-r', CVSTAG, builder.NEWVERS_PATH])

        return d

    def _cvsFailure(self, failure):
        self.assert_(isinstance(failure.value, builder.CVSCommandError))

    def test_failureHandling(self):
        d = defer.Deferred()
        pp = builder.NCVSBuildnameProcessProtocol(d)
        d.addErrback(self._cvsFailure)

        reactor.spawnProcess(pp, builder.CVS_PATH, [builder.CVS_PATH, 'die horribly'])

        return d

class ReleaseBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.builder = builder.ReleaseBuilder(CVSROOT, CVSTAG, BUILDROOT)
        self.log = open(MAKE_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(MAKE_LOG)
        os.unlink(MAKE_OUT)

    def _buildResult(self, result):
        o = open(MAKE_OUT, 'r')
        self.assertEquals(o.read(), 'ReleaseBuilder: 6.0-RELEASE-p4 %s %s %s no no\n' % (CHROOT, CVSROOT, CVSTAG))
        o.close()
        self.assertEquals(result, 0)

    def test_build(self):
        d = self.builder.build(self.log)
        d.addCallback(self._buildResult)
        return d
