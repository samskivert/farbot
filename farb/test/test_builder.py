# test_builder.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2006-2008 Three Rings Design, Inc.
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
import shutil
import unittest

import farb
from farb import builder, utils

# Useful Constants
from farb.test import DATA_DIR, CMD_DIR, rewrite_config

FREEBSD_REL_PATH = os.path.join(DATA_DIR, 'buildtest')
PROCESS_LOG = os.path.join(FREEBSD_REL_PATH, 'process.log')
PROCESS_OUT = os.path.join(FREEBSD_REL_PATH, 'process.out')

BUILDROOT = os.path.join(DATA_DIR, 'buildtest')
RELEASEROOT = os.path.join(BUILDROOT, 'releaseroot')
PKGROOT = os.path.join(BUILDROOT, 'pkgroot')
CVSROOT = os.path.join(DATA_DIR, 'fakencvs')
INSTALLROOT = os.path.join(DATA_DIR, 'netinstall')
TFTPROOT = os.path.join(DATA_DIR, 'test_tftproot')
CVSTAG = 'RELENG_6_0'
CVSTAG_OLD = 'RELENG_5_3'
EXPORT_FILE = os.path.join(BUILDROOT, 'newvers.sh')
INSTALL_CFG = os.path.join(DATA_DIR, 'test_configs', 'install.cfg')
ISO_MOUNTPOINT = os.path.join(DATA_DIR, 'fake_iso_mount')
CDROM_INF_IN = os.path.join(DATA_DIR, 'test_configs', 'cdrom.inf.in')
CDROM_INF = os.path.join(ISO_MOUNTPOINT, 'cdrom.inf')

MDCONFIG_PATH = os.path.join(CMD_DIR, 'mdconfig.sh')
CHROOT_PATH = os.path.join(CMD_DIR, 'chroot.sh')
MOUNT_PATH = os.path.join(CMD_DIR, 'mount.sh')
UMOUNT_PATH = os.path.join(CMD_DIR, 'umount.sh')
PORTSNAP_PATH = os.path.join(CMD_DIR, 'portsnap.sh')
TAR_PATH = os.path.join(CMD_DIR, 'tar.sh')
CHFLAGS_PATH = os.path.join(CMD_DIR, 'chflags.sh')
ECHO_PATH = '/bin/echo'
SH_PATH = '/bin/sh'
ROOT_PATH = os.path.join(DATA_DIR, 'fake_root')

# Reach in and tweak various path constants
builder.FREEBSD_REL_PATH = FREEBSD_REL_PATH
builder.MDCONFIG_PATH = MDCONFIG_PATH
builder.CHROOT_PATH = CHROOT_PATH
builder.MOUNT_PATH = MOUNT_PATH
builder.UMOUNT_PATH = UMOUNT_PATH
builder.PORTSNAP_PATH = PORTSNAP_PATH
builder.TAR_PATH = TAR_PATH
builder.CHFLAGS_PATH = CHFLAGS_PATH
builder.ROOT_PATH = ROOT_PATH

class CVSCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        os.unlink(EXPORT_FILE)
        os.unlink(PROCESS_LOG)
        shutil.rmtree(os.path.join(BUILDROOT, 'CVS'))

    def test_cvsCheckout(self):
        cvs = builder.CVSCommand(CVSROOT)
        cvs.checkout(CVSTAG, builder.NEWVERS_PATH, BUILDROOT, self.log)
        self.assert_(os.path.exists(EXPORT_FILE))

    # Make sure cvs.checkout can handle updating an older version of an already
    # checked out file.
    def test_cvsUpdate(self):
        cvs = builder.CVSCommand(CVSROOT)
        cvs.checkout(CVSTAG_OLD, builder.NEWVERS_PATH, BUILDROOT, self.log)
        cvs.checkout(CVSTAG, builder.NEWVERS_PATH, BUILDROOT, self.log)
        self.assert_(os.path.exists(EXPORT_FILE))

class MountCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.mc = builder.MountCommand('/dev/md0', '/mnt/md0')

    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)

    def test_mount(self):
        self.mc.mount(self.log)
        self.log.seek(0)
        self.assertEquals(self.log.read(), '/dev/md0\n/mnt/md0\n')

    def test_umount(self):
        self.mc.umount(self.log)

class MountCommandTypeTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.mc = builder.MountCommand('devfs', '/dev', fstype='devfs')

    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)

    def test_mount(self):
        self.mc.mount(self.log)
        self.log.seek(0)
        self.assertEquals(self.log.read(), 'devfs\n/dev\ndevfs\n')

class MDMountCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.mdc = builder.MDConfigCommand('/nonexistent')
        self.mc = builder.MDMountCommand(self.mdc, '/mnt/md0')

    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)

    def test_mount(self):
        self.mc.mount(self.log)

    def test_umount(self):
        # The mdconfig device needs to be attached before we can detach it.
        self.mdc.attach(self.log)
        self.mc.umount(self.log)

class MakeCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)
        os.unlink(PROCESS_LOG)

    def test_make(self):
        makeOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }
        mc = builder.MakeCommand(BUILDROOT, ('makecommand',), makeOptions)
        mc.make(self.log)
        o = open(PROCESS_OUT, 'r')
        self.assertEquals('MakeCommand 1 2\n', o.read())
        o.close()

    def test_makeMultiple(self):
        makeOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }
        mc = builder.MakeCommand(BUILDROOT, ('makecommand','makecommand'), makeOptions)
        mc.make(self.log)
        o = open(PROCESS_OUT, 'r')
        self.assertEquals('MakeCommand 1 2\n', o.read())
        o.close()
    
    def test_makeChroot(self):
        (head, tail) = os.path.split(BUILDROOT)
        mc = builder.MakeCommand(os.path.sep + tail, ('makecommand',), chrootdir=head) 
        mc.make(self.log)
        self.log.seek(0)
        # take just the first line as make tells us what directories it
        # is entering and exiting on certain platforms
        self.assertEquals(self.log.read().splitlines(1)[0], '%s %s %s -C %s makecommand\n' % (CHROOT_PATH, head, builder.MAKE_PATH, os.path.sep + tail))

class PortsnapCommandTestCase(unittest.TestCase):
	def setUp(self):
	    self.log = open(PROCESS_LOG, 'w+')
	    self.pc = builder.PortsnapCommand()

	def tearDown(self):
	    self.log.close()
		os.unlink(PROCESS_LOG)

    def test_fetch(self):
        self.pc.fetch(self.log)
        
    def test_extract(self):
        self.pc.extract('/nonexistent', self.log)

class ChflagsCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.cc = builder.ChflagsCommand('/nonexistent')
    
    def tearDown(self):
        self.log.close()
        os.unlink(PROCESS_LOG)
    
    def test_removeAll(self):
        self.cc.removeAll(self.log)

class MDConfigCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.mdc = builder.MDConfigCommand('/nonexistent')
        self.log = open(PROCESS_LOG, 'w+')

    def test_attach(self):
        self.mdc.attach(self.log)
        self.assertEquals(self.mdc.md, 'md0')

    def test_detach(self):
        self.mdc.attach(self.log)
        self.mdc.detach(self.log)
    
    def test_detachNonexistent(self):
        self.assertRaises(builder.MDConfigCommandError, self.mdc.detach, self.log)
    
    def test_doubleAttach(self):
        self.mdc.attach(self.log)
        self.assertRaises(builder.MDConfigCommandError, self.mdc.attach, self.log)

class ChrootCleanerTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.cleaner = builder.ChrootCleaner(RELEASEROOT)
    
    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)
    
    def _dirCreated(self):
        self.assert_(os.path.isdir(RELEASEROOT))
        self.assertEquals(len(os.listdir(RELEASEROOT)), 0)
    
    def test_cleanNonexistent(self):
        # Make sure we don't choke if the chroot doesn't already exist, and 
        # that a new empty one gets created
        self.cleaner.clean(self.log)
        self._dirCreated()
    
    def test_clean(self):
        # Now try the same thing with a chroot that isn't empty
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        utils.copyRecursive(ISO_MOUNTPOINT, os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH))
        self.cleaner.clean(self.log)
        self._dirCreated()

class ReleaseBuilderTestCase(unittest.TestCase):
    def setUp(self):
        self.builder = builder.ReleaseBuilder(CVSROOT, CVSTAG, RELEASEROOT, makecds=True)
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)

    def test_getBuildName(self):
        buildname = self.builder._getBuildName(self.log)
        self.assertEquals('6.0-RELEASE-p4', buildname)

    def test_build(self):
        self.builder.build(self.log)
        o = open(PROCESS_OUT, 'r')
        self.assertEquals(o.read(), 'ReleaseBuilder: 6.0-RELEASE-p4 %s %s %s no no yes\n' % (RELEASEROOT, CVSROOT, CVSTAG))
        o.close()

    def test_buildFailure(self):
        # Reach into our builder and force an implosion
        self.builder.makeTarget = ('error',)
        self.assertRaises(builder.ReleaseBuildError, self.builder.build, self.log)

    def test_cvsFailure(self):
        # Reach into our builder and force a CVS implosion
        self.builder.cvsroot = 'nonexistent'
        self.assertRaises(builder.ReleaseBuildError, self.builder.build, self.log)

class ISOReaderTestCase(unittest.TestCase):
    def setUp(self):
        self.reader = builder.ISOReader(ISO_MOUNTPOINT, RELEASEROOT)
        self.log = open(PROCESS_LOG, 'w+')
    
    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
    
    def _copyResult(self):
        distdir = os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH, '6.2-RELEASE')
        bootdir = os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH, 'boot')
        self.assert_(os.path.exists(os.path.join(distdir, 'base', 'base.aa')))
        self.assert_(os.path.exists(os.path.join(distdir, 'base', 'base.ab')))
        self.assert_(os.path.exists(os.path.join(distdir, 'base', 'base.ac')))
        self.assert_(os.path.exists(os.path.join(distdir, 'src', 'swtf.aa')))
        self.assert_(os.path.exists(os.path.join(distdir, 'src', 'swtf.ab')))
        self.assert_(os.path.exists(os.path.join(distdir, 'src', 'szomg.aa')))
        self.assert_(os.path.exists(os.path.join(distdir, 'src', 'szomg.ab')))
        self.assert_(os.path.exists(os.path.join(bootdir, 'mfsroot.gz')))
        self.assert_(os.path.exists(os.path.join(bootdir, 'kernel', 'kernel')))
        self.assert_(not os.path.exists(os.path.join(RELEASEROOT, 'afile')))
    
    def test_copy(self):
        # Try copying the dists from the CD into the release root
        self.reader.copy(self.log)
        self._copyResult()
    
    def test_copyReplace(self):
        # Now try copying when there is already something in RELEASEROOT
        os.mkdir(RELEASEROOT)
        f = open(os.path.join(RELEASEROOT, 'afile'), 'w')
        f.close()
        self.reader.copy(self.log)
        self._copyResult()

class PackageChrootAssemblerTestCase(unittest.TestCase):
    def setUp(self):
        self.assembler = builder.PackageChrootAssembler(RELEASEROOT, PKGROOT)
        self.log = open(PROCESS_LOG, 'w+')
        self.dists = {'base' : ['base'], 'src' : ['szomg', 'swtf']}
        # Copy in a release to RELEASEROOT
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        utils.copyRecursive(ISO_MOUNTPOINT, os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH))
    
    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)
        if (os.path.exists(PKGROOT)):
            shutil.rmtree(PKGROOT)
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)
    
    def _extractResult(self):
        self.assert_(os.path.exists(os.path.join(PKGROOT, 'usr', 'src', 'wtf.c')))
        self.assert_(os.path.exists(os.path.join(PKGROOT, 'usr', 'src', 'zomg.c')))
        self.assert_(os.path.exists(os.path.join(PKGROOT, 'usr', 'bin', 'foo.sh')))
        self.assert_(os.path.exists(os.path.join(PKGROOT, 'usr', 'bin', 'bar.sh')))
        self.assert_(os.path.exists(os.path.join(PKGROOT, builder.RESOLV_CONF)))
        self.assert_(not os.path.exists(os.path.join(PKGROOT, 'afile')))

    def test_extract(self):
        # Try actually extracting a fake base dist into the chroot.
        self.assembler.extract(self.dists, self.log)
        self._extractResult()
    
    def test_extractReplace(self):
        # Try extracting when the chroot already exists
        os.mkdir(PKGROOT)
        f = open(os.path.join(PKGROOT, 'afile'), 'w')
        f.close()
        self.assembler.extract(self.dists, self.log)
        self._extractResult()

class PackageBuilderTestCase(unittest.TestCase):
    def setUp(self):
        buildOptions = {
            'TEST1' : '1',
            'TEST2' : '2'
        }
        self.builder = builder.PackageBuilder('', BUILDROOT, buildOptions)
        self.log = open(PROCESS_LOG, 'w+')

    def tearDown(self):
        self.log.close()
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)
        if (os.path.exists(PROCESS_OUT)):
            os.unlink(PROCESS_OUT)

    def test_build(self):
        self.builder.build(self.log)
        o = open(PROCESS_OUT, 'r')
        self.assertEquals(o.read(), 'PackageBuilder: 1 2\n')
        o.close()
    
    def test_buildFailure(self):
        # Reach into our builder and force an implosion
        self.builder.makeTarget = ('error',)
        self.assertRaises(builder.PackageBuildError, self.builder.build, self.log)

class InstallAssemblerTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.destdir = os.path.join(TFTPROOT, 'testinstall')
        self.mfsroot = os.path.join(self.destdir, 'mfsroot')
        self.installCfg = os.path.join(self.destdir, 'mnt', 'install.cfg')
        self.bootConf = os.path.join(self.destdir, 'boot.conf')
        self.builder = builder.InstallAssembler('testinstall', 'Test Install', RELEASEROOT, INSTALL_CFG)

        os.mkdir(TFTPROOT)
        os.mkdir(self.destdir)
        
        # Create dummy "release" containing the kernel and mfsroot needed
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        utils.copyRecursive(ISO_MOUNTPOINT, os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH))

    def tearDown(self):
        self.log.close()

        # Clean up process log
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)

        # Clean up builder output
        if (os.path.exists(TFTPROOT)):
            shutil.rmtree(TFTPROOT)
        if (os.path.exists(self.destdir)):
            shutil.rmtree(self.destdir)
        
        # Remove dummy release
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)

    def test_build(self):
        self.builder.build(self.destdir, self.log)
        
        # Make sure the gunzip worked
        o = open(self.mfsroot, 'r')
        self.assertEquals(o.read(), 'Uncompress worked.\n')
        o.close()

        # Check to see if the install.cfg got copied to the mountPoint
        self.assert_(os.path.exists(self.installCfg))

        # Check to see if the kernel module was copied
        kmod = os.path.join(self.destdir, 'kernel', 'righthook.ko')
        self.assert_(os.path.exists(kmod))

        # Check to see if boot.conf was created
        self.assert_(os.path.exists(self.bootConf))

    def test_buildFailure(self):
        # Reach into our builder and force an implosion
        self.builder.mfsCompressed = '/nonexistent'
        self.assertRaises(builder.InstallAssembleError, self.builder.build, self.destdir, self.log)

class ReleaseAssemblerTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.destdir = os.path.join(INSTALLROOT, 'buildtest')
        # Create dummy "release"
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        utils.copyRecursive(ISO_MOUNTPOINT, os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH))

    def tearDown(self):
        self.log.close()

        # Clean up process log
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)

        # Clean up the install root
        if (os.path.exists(INSTALLROOT)):
            shutil.rmtree(INSTALLROOT)
        
        # Remove dummy release
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)

    def test_build(self):
        rib = builder.ReleaseAssembler('6.2', RELEASEROOT, PKGROOT)
        rib.build(self.destdir, self.log)
        
        # Verify that the release data was copied over
        self.assert_(os.path.exists(os.path.join(self.destdir, 'base', 'base.aa')))

        # Verify that the package installation script was copied and is 
        # executable
        self.assert_(os.path.exists(os.path.join(self.destdir, os.path.basename(farb.INSTALL_PACKAGE_SH))))
        self.assert_(os.access(os.path.join(self.destdir, os.path.basename(farb.INSTALL_PACKAGE_SH)), os.X_OK))

        # Verify that the local directory was not created
        self.assert_(not os.path.exists(os.path.join(self.destdir, 'local')))

    def test_buildLocalData(self):
        # Copy in a regular file and a directory
        localData = [RELEASEROOT, INSTALL_CFG]
        rib = builder.ReleaseAssembler('6.2', RELEASEROOT, PKGROOT, localData)
        rib.build(self.destdir, self.log)
        # Verify that the localdata file was copied
        self.assert_(os.path.exists(os.path.join(self.destdir, 'local', os.path.basename(INSTALL_CFG))))

        # Verify that the localdata directory was copied
        self.assert_(os.path.exists(os.path.join(self.destdir, 'local', RELEASEROOT, builder.RELEASE_CD_PATH, '6.2-RELEASE', 'base', 'base.aa')))

class NetInstallAssemblerTestCase(unittest.TestCase):
    def setUp(self):
        self.log = open(PROCESS_LOG, 'w+')
        self.installs = [builder.InstallAssembler('testinstall', 'Test Install', RELEASEROOT, INSTALL_CFG),]
        self.releaseInstalls = [builder.ReleaseAssembler('6.2', RELEASEROOT, PKGROOT),]
        self.irb = builder.NetInstallAssembler(INSTALLROOT, self.releaseInstalls, self.installs)
        # Create dummy "release" to copy to netinstall directory
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        utils.copyRecursive(ISO_MOUNTPOINT, os.path.join(RELEASEROOT, builder.RELEASE_CD_PATH))
    
    def tearDown(self):
        self.log.close()

        # Clean up process log
        if (os.path.exists(PROCESS_LOG)):
            os.unlink(PROCESS_LOG)

        # Clean up builder output
        if (os.path.exists(INSTALLROOT)):
            shutil.rmtree(INSTALLROOT)

        # Remove dummy release
        if (os.path.exists(RELEASEROOT)):
            shutil.rmtree(RELEASEROOT)
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)

    def test_build(self):
        self.irb.build(self.log)

        ## Verify Per-Release Data
        # Verify that the release data was copied over
        self.assert_(os.path.exists(os.path.join(INSTALLROOT, '6.2', 'base', 'base.aa')))

        tftproot = os.path.join(INSTALLROOT, 'tftproot')

        ## Verify Per-Install Data
        # Check to see if the install kernel module was copied
        kmod = os.path.join(tftproot, 'testinstall', 'kernel', 'righthook.ko')
        self.failUnless(os.path.exists(kmod), msg='The pre-install kernel was not copied to the tftproot directory.')

        # Check to see if boot.conf was created
        self.failUnless(os.path.exists(os.path.join(tftproot, 'testinstall', 'boot.conf')), msg='The per-install boot.conf file was not created.')

        ## Verify shared boot loader data
        # Check to see if the bootloader was copied over
        self.failUnless(os.path.exists(os.path.join(tftproot, 'boot')), msg='The shared boot loader was not copied to the tftproot directory.')

        # Check for netinstall.4th, loader.conf, and loader.rc
        self.failUnless(os.path.exists(os.path.join(tftproot, 'boot', 'netinstall.4th')), msg='The netinstall.4th file was not generated in the tftproot directory.')
        self.failUnless(os.path.exists(os.path.join(tftproot, 'boot', 'loader.conf')), msg='The FarBot loader.conf file was not copied to the tftproot directory.')
        self.failUnless(os.path.exists(os.path.join(tftproot, 'boot', 'loader.rc')), msg='The FarBot loader.rc file was not copied to the tftproot directory.')

class GetCDReleaseTestCase(unittest.TestCase):
    def tearDown(self):
        if (os.path.exists(CDROM_INF)):
            os.unlink(CDROM_INF)
    
    def test_getCDRelease(self):
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'CD_VERSION = 6.2-RELEASE'})
        self.assertEquals(builder._getCDRelease(os.path.dirname(CDROM_INF)), '6.2-RELEASE')
    
    def test_badCDInf(self):
        # Make sure we have an exception when CD_VERSION line looks wrong
        rewrite_config(CDROM_INF_IN, CDROM_INF, {'@CD_VERSION_LINE@' : 'hi I am a CD!'})
        self.assertRaises(builder.CDReleaseError, builder._getCDRelease, os.path.dirname(CDROM_INF))
    
    def test_missingCDInf(self):
        # Also make sure we get an exception also when there is no cdrom.inf
        self.assertRaises(builder.CDReleaseError, builder._getCDRelease, os.path.dirname(CDROM_INF))
