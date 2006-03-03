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
from farb.test import DATA_DIR, CMD_DIR

FREEBSD_REL_PATH = os.path.join(DATA_DIR, 'buildtest')
MAKE_LOG = os.path.join(FREEBSD_REL_PATH, 'make.log')
MAKE_OUT = os.path.join(FREEBSD_REL_PATH, 'make.out')

BUILDROOT = os.path.join(DATA_DIR, 'buildtest')
CHROOT = os.path.join(BUILDROOT, 'chroot')
CVSROOT = os.path.join(DATA_DIR, 'fakencvs')
CVSTAG = 'RELENG_6_0'

MDCONFIG_PATH = os.path.join(CMD_DIR, 'mdconfig.sh')
CHROOT_PATH = os.path.join(CMD_DIR, 'chroot.sh')

# Reach in and tweak various path constants
builder.FREEBSD_REL_PATH = FREEBSD_REL_PATH
builder.MDCONFIG_PATH = MDCONFIG_PATH
builder.CHROOT_PATH = CHROOT_PATH

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
        if (os.path.exists(MAKE_OUT)):
            os.unlink(MAKE_OUT)
        os.unlink(MAKE_LOG)

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

    def _makeChrootResult(self, result):
        self.log.seek(0)
        self.assertEquals(CHROOT_PATH + ' /nonexistant ' + builder.MAKE_PATH + ' -C ' + BUILDROOT + ' makecommand\n', self.log.read())
        self.assertEquals(result, 0)

    def test_makeChroot(self):
        mc = builder.MakeCommand(BUILDROOT, 'makecommand', {}, '/nonexistant') 
        d = mc.make(self.log) 
        d.addCallback(self._makeChrootResult)
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

class MDConfigProcessProtocolTestCase(unittest.TestCase):
    def _mdResult(self, result):
        self.assertEquals(result, 'md0')

    def test_attach(self):
        d = defer.Deferred()
        pp = builder.MDConfigProcessProtocol(d)
        d.addCallback(self._mdResult)

        reactor.spawnProcess(pp, MDCONFIG_PATH, [MDCONFIG_PATH, '-a', '-t', 'vnode', '-f', '/nonexistent'])

        return d

    def _mdDetachResult(self, result):
        pass

    def test_detach(self):
        d = defer.Deferred()
        pp = builder.MDConfigProcessProtocol(d)
        d.addCallback(self._mdDetachResult)

        reactor.spawnProcess(pp, MDCONFIG_PATH, [MDCONFIG_PATH, '-d', '-u', 'md0'])

        return d

    def _mdFailure(self, failure):
        self.assert_(isinstance(failure.value, builder.MDConfigCommandError))

    def test_failureHandling(self):
        d = defer.Deferred()
        pp = builder.MDConfigProcessProtocol(d)
        d.addErrback(self._mdFailure)

        reactor.spawnProcess(pp, MDCONFIG_PATH, [MDCONFIG_PATH, 'die horribly'])

        return d

class MDConfigCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.mdc = builder.MDConfigCommand('/nonexistent')

    def _cbAttachResult(self, result):
        self.assertEquals(self.mdc.md, 'md0')

    def test_attach(self):
        d = self.mdc.attach()
        d.addCallback(self._cbAttachResult)
        return d

    def _cbAttachDetachResult(self, result):
        d = self.mdc.detach()
        return d

    def test_detach(self):
        d = self.mdc.attach()
        d.addCallback(self._cbAttachDetachResult)
        return d

class ReleaseBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.builder = builder.ReleaseBuilder(CVSROOT, CVSTAG, BUILDROOT, makecds=True)
        self.log = open(MAKE_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(MAKE_LOG)):
            os.unlink(MAKE_LOG)
        if (os.path.exists(MAKE_OUT)):
            os.unlink(MAKE_OUT)

    def _buildResult(self, result):
        o = open(MAKE_OUT, 'r')
        self.assertEquals(o.read(), 'ReleaseBuilder: 6.0-RELEASE-p4 %s %s %s no no yes\n' % (CHROOT, CVSROOT, CVSTAG))
        o.close()
        self.assertEquals(result, 0)

    def test_build(self):
        d = self.builder.build(self.log)
        d.addCallback(self._buildResult)
        return d

    def _buildSuccess(self, result):
        self.fail("This call should not have succeeded")

    def _buildError(self, failure):
        failure.trap(builder.ReleaseBuildError)

    def test_buildFailure(self):
        # Reach into our builder and force an implosion
        self.builder.makeTarget = 'error'
        d = self.builder.build(self.log)
        d.addCallbacks(self._buildSuccess, self._buildError)
        return d

    def _buildCVSSuccess(self, result):
        self.fail("This call should not have succeeded")

    def _buildCVSError(self, failure):
        failure.trap(builder.ReleaseBuildError)

    def test_cvsFailure(self):
        # Reach into our builder and force a CVS implosion
        self.builder.cvsroot = 'nonexistent'
        d = self.builder.build(self.log)
        d.addCallbacks(self._buildCVSSuccess, self._buildCVSError)
        return d
