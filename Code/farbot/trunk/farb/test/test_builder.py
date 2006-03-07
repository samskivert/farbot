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
PROCESS_LOG = os.path.join(FREEBSD_REL_PATH, 'process.log')
PROCESS_OUT = os.path.join(FREEBSD_REL_PATH, 'process.out')

BUILDROOT = os.path.join(DATA_DIR, 'buildtest')
CHROOT = os.path.join(BUILDROOT, 'chroot')
CVSROOT = os.path.join(DATA_DIR, 'fakencvs')
CVSTAG = 'RELENG_6_0'
EXPORT_FILE = os.path.join(BUILDROOT, 'newvers.sh')

MDCONFIG_PATH = os.path.join(CMD_DIR, 'mdconfig.sh')
CHROOT_PATH = os.path.join(CMD_DIR, 'chroot.sh')
MOUNT_PATH = os.path.join(CMD_DIR, 'mount.sh')
UMOUNT_PATH = os.path.join(CMD_DIR, 'umount.sh')
ECHO_PATH = '/bin/echo'
SH_PATH = '/bin/sh'

# Reach in and tweak various path constants
builder.FREEBSD_REL_PATH = FREEBSD_REL_PATH
builder.MDCONFIG_PATH = MDCONFIG_PATH
builder.CHROOT_PATH = CHROOT_PATH
builder.MOUNT_PATH = MOUNT_PATH
builder.UMOUNT_PATH = UMOUNT_PATH

class LoggingProcessProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)

    def _processResult(self, result):
        self.log.seek(0)
        self.assertEquals('hello\n', self.log.read())
        self.assertEquals(result, 0)

    def test_spawnProcess(self):
        d = defer.Deferred()
        pp = builder.LoggingProcessProtocol(d, self.log)
        d.addCallback(self._processResult)

        reactor.spawnProcess(pp, ECHO_PATH, [ECHO_PATH, 'hello'])
        return d

    def _processSuccess(self, result):
        self.fail("This call should not have succeeded")

    def _processError(self, result):
        self.assertNotEqual(result, 0)

    def test_processError(self):
        d = defer.Deferred()
        pp = builder.LoggingProcessProtocol(d, self.log)
        d.addCallbacks(self._processSuccess, self._processError)

        reactor.spawnProcess(pp, SH_PATH, [SH_PATH, '-c', 'exit 5'])
        return d

class CVSCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(EXPORT_FILE)
        os.unlink(PROCESS_LOG)

    def _cvsResult(self, result):
        self.assertEquals(os.path.exists(EXPORT_FILE), 1)
        self.assertEquals(result, 0)

    def test_cvs(self):
        cvs = builder.CVSCommand(CVSROOT)
        d = cvs.export(CVSTAG, builder.NEWVERS_PATH, BUILDROOT, self.log)
        d.addCallback(self._cvsResult)

        return d

class MountCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.mc = builder.MountCommand()

    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)

    def _cbMountResult(self, result):
        self.assertEquals(result, 0)

    def test_mount(self):
        d = self.mc.mount('/dev/md0', '/mnt/md0', self.log)
        d.addCallback(self._cbMountResult)
        return d

    def _cbUmountResult(self, result):
        self.assertEquals(result, 0)

    def test_umount(self):
        d = self.mc.umount('/mnt/md0', self.log)
        d.addCallback(self._cbUmountResult)
        return d

class MakeCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)
        os.unlink(PROCESS_LOG)

    def _makeResult(self, result):
        o = open(PROCESS_OUT, 'r')
        self.assertEquals('MakeCommand 1 2\n', o.read())
        o.close()
        self.assertEquals(result, 0)

    def test_make(self):
        makeOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }

        mc = builder.MakeCommand(BUILDROOT, ('makecommand',), makeOptions)
        d = mc.make(self.log)
        d.addCallback(self._makeResult)

        return d

    def _makeMultipleResult(self, result):
        o = open(PROCESS_OUT, 'r')
        self.assertEquals('MakeCommand 1 2\nMakeCommand 1 2\n', o.read())
        o.close()
        self.assertEquals(result, 0)

    def test_makeMultiple(self):
        makeOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }

        mc = builder.MakeCommand(BUILDROOT, ('makecommand','makecommand'), makeOptions)
        d = mc.make(self.log)
        d.addCallback(self._makeResult)

        return d

    def _makeChrootResult(self, result):
        self.log.seek(0)
        # take just the first line as make tells us what directories it
        # is entering and exiting on certain platforms
        self.assertEquals(self.log.read().splitlines(1)[0], '%s /nonexistant %s -C %s makecommand\n' % (CHROOT_PATH, builder.MAKE_PATH, BUILDROOT))
        self.assertEquals(result, 0)

    def test_makeChroot(self):
        mc = builder.MakeCommand(BUILDROOT, ('makecommand',), {}, '/nonexistant') 
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
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)

    def _buildResult(self, result):
        o = open(PROCESS_OUT, 'r')
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
        self.builder.makeTarget = ('error',)
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

class PackageBuilderTestCase(unittest.TestCase):
    def setUp(self):
        buildOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }
        self.builder = builder.PackageBuilder(CHROOT, BUILDROOT, buildOptions)
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)

    def _buildResult(self, result):
        o = open(PROCESS_OUT, 'r')
        self.assertEquals(o.read(), 'PackageBuilder: 1 2\n')
        o.close()
        self.assertEquals(result, 0)

    def test_build(self):
        d = self.builder.build(self.log)
        d.addCallback(self._buildResult)
        return d

    def _buildSuccess(self, result):
        self.fail("This call should not have succeeded")

    def _buildError(self, failure):
        failure.trap(builder.PackageBuildError)

    def test_buildFailure(self):
        # Reach into our builder and force an implosion
        self.builder.makeTarget = ('error',)
        d = self.builder.build(self.log)
        d.addCallbacks(self._buildSuccess, self._buildError)
        return d
