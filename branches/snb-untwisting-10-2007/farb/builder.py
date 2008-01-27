# builder.py vi:ts=4:sw=4:expandtab:
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

import cStringIO
import exceptions
import glob
import gzip
import os
import re
import shutil
import subprocess

import farb
from farb import utils

# make(1) path
MAKE_PATH = '/usr/bin/make'

# chroot(8) path
CHROOT_PATH = '/usr/sbin/chroot'

# cvs(1) path
CVS_PATH = '/usr/bin/cvs'

# mdconfig(8) path
MDCONFIG_PATH = '/sbin/mdconfig'

# mount(8) path
MOUNT_PATH = '/sbin/mount'

# umount(8) path
UMOUNT_PATH = '/sbin/umount'

# portsnap(8) path
PORTSNAP_PATH = '/usr/sbin/portsnap'

# tar(1) path
TAR_PATH = '/usr/bin/tar'

# chflags(1) path
CHFLAGS_PATH = '/bin/chflags'

# Standard FreeBSD src location
FREEBSD_REL_PATH = '/usr/src/release'

# Standard FreeBSD ports location
FREEBSD_PORTS_PATH = '/usr/ports'

# Relative path of newvers.sh file in the FreeBSD CVS repository
NEWVERS_PATH = 'src/sys/conf/newvers.sh'

# Release root-relative path to the contents of the first install CD
RELEASE_CD_PATH = 'R/cdrom/disc1'

# Package chroot-relative path to the package directory
RELEASE_PACKAGE_PATH = 'usr/ports/packages'

# Path to root of filesystem. This is mostly here to override in unit tests
ROOT_PATH = '/'

# Releative path for /etc/resolv.conf
RESOLV_CONF = 'etc/resolv.conf'

# Default Root Environment
ROOT_ENV = {
    'USER'      : 'root',
    'GROUP'     : 'wheel',
    'HOME'      : '/root',
    'LOGNAME'   : 'root',
    'PATH'      : '/sbin:/bin:/usr/sbin:/usr/bin:/usr/games:/usr/local/sbin:/usr/local/bin:/usr/X11R6/bin:/root/bin',
    'FTP_PASSIVE_MODE' : 'YES'
}

# Exceptions
class CommandError(farb.FarbError):
    pass

class CVSCommandError(CommandError):
    pass

class MountCommandError(CommandError):
    pass

class NCVSParseError(CVSCommandError):
    pass

class MDConfigCommandError(CommandError):
    pass

class MakeCommandError(CommandError):
    pass

class PortsnapCommandError(CommandError):
    pass

class ChflagsCommandError(CommandError):
    pass

class TarCommandError(CommandError):
    pass

class ReleaseBuildError(farb.FarbError):
    pass

class ISOReaderError(farb.FarbError):
    pass

class PackageChrootAssemblerError(farb.FarbError):
    pass

class PackageBuildError(farb.FarbError):
    pass

class InstallAssembleError(farb.FarbError):
    pass

class ReleaseAssembleError(farb.FarbError):
    pass

class NetInstallAssembleError(farb.FarbError):
    pass

class CDReleaseError(farb.FarbError):
    pass

class ChrootCleanerError(farb.FarbError):
    pass

class MDConfigCommand(object):
    """
    mdconfig(8) command context
    """
    def __init__(self, file):
        """
        Create a new MDConfigCommand vnode instance
        @param file: File to attach
        """
        self.file = file
        self.md = None

    def attach(self, log):
        """
        Attach the file to an md(4) device
        """
        if self.md:
            raise MDConfigCommandError, "Cannot attach md device for %s because it has already been attached" % self.file

        # Create command argv, and run it. Save the device name mdconfig prints
        argv = [MDCONFIG_PATH, '-a', '-t', 'vnode', '-f', self.file]
        device = _runCommand(argv, log, MDConfigCommandError, ROOT_ENV, True)
        self.md = device.rstrip('\n')

    def detach(self, log):
        """
        Attach the file to an md(4) device
        """
        if self.md == None:
            raise MDConfigCommandError, "Cannot detach md device for %s because it doesn't exist" % self.file

        # Create command argv, then run it
        argv = [MDCONFIG_PATH, '-d', '-u', self.md]
        _runCommand(argv, log, MDConfigCommandError, ROOT_ENV)

class CVSCommand(object):
    """
    cvs(1) command context
    """
    def __init__(self, repository):
        """
        Create a new CVSCommand instance
        @param repository: CVS repository to use 
        """
        self.repository = repository

    def checkout(self, release, module, destination, log):
        """
        Run cvs(1) checkout
        @param release: release to checkout, ex. HEAD 
        @param module: module to use, ex: ports 
        @param destination: destination for the checkout 
        @param log: Open log file
        """
        # Create command argv, and run it
        argv = [CVS_PATH, '-R', '-d', self.repository, 'checkout', '-r', release, '-d', destination, module]
        _runCommand(argv, log, CVSCommandError, ROOT_ENV)

class MountCommand(object):
    """
    mount(8)/umount(8) command context
    """
    def __init__(self, device, mountpoint, fstype=None):
        """
        Create a new MountCommand instance
        @param device: device to mount
        @param mountpoint: mount point
        @param fstype: File system type. If unspecified, mount(8) will
        try to figure it out.
        """
        self.device = device
        self.mountpoint = mountpoint
        self.fstype = fstype

    def mount(self, log):
        """
        Run mount(8)
        @param log: Open log file
        """

        # Create command argv
        if (self.fstype):
            argv = [MOUNT_PATH, '-t', self.fstype, self.device, self.mountpoint]
        else:
            argv = [MOUNT_PATH, self.device, self.mountpoint]

        # And run it
        _runCommand(argv, log, MountCommandError, ROOT_ENV)

    def umount(self, log):
        """
        Run umount(8)
        @param log: Open log file
        """

        # Create command argv and execute
        argv = [UMOUNT_PATH, self.mountpoint]
        _runCommand(argv, log, MountCommandError, ROOT_ENV)


class MDMountCommand(MountCommand):
    """
    mount(8)/umount(8) command context
    """
    def __init__(self, mdc, mountpoint, fstype=None):
        """
        Create a new MountCommand instance
        @param mdc: MDConfigCommand instance
        @param mountpoint: mount point
        @param fstype: File system type. If unspecified, mount(8) will
        try to figure it out.
        """
        self.mdc = mdc
        super(MDMountCommand, self).__init__(None, mountpoint, fstype)

    def mount(self, log):
        """
        Attach the device, run mount(8)
        @param log: Open log file
        """
        # Attach the image. Let the caller handle MDConfigCommand exceptions 
        # directly
        self.mdc.attach(log)
        # Build the device path and mount it
        self.device = os.path.join('/dev/', self.mdc.md)
        super(MDMountCommand, self).mount(log)

    def umount(self, log):
        """
        Run unmount(8), detach the image.
        @param log: Open log file
        """
        # Unmount and detach the image
        super(MDMountCommand, self).umount(log)
        self.mdc.detach(log)

class MakeCommand(object):
    """
    make(1) command context
    """
    def __init__(self, directory, targets, options={}, chrootdir=None):
        """
        Create a new MakeCommand instance
        @param directory: Directory in which to run make(1)
        @param targets: Makefile targets
        @param options: Dictionary of Makefile options
        @param chrootdir: Optional chroot directory
        """
        self.directory = directory
        self.targets = targets
        self.options = options
        self.chrootdir = chrootdir

    def make(self, log):
        """
        Run make(1)
        @param log: Open log file
        """

        # Create command argv
        argv = [MAKE_PATH, '-C', self.directory]
        if self.chrootdir:
            argv.insert(0, self.chrootdir)
            argv.insert(0, CHROOT_PATH)

        for target in self.targets:
            argv.append(target)

        for option, value in self.options.items():
            argv.append("%s=%s" % (option, value))
        
        # Run it
        _runCommand(argv, log, MakeCommandError, ROOT_ENV)

class PortsnapCommand(object):
    """
    portsnap(8) command context
    """
    def fetch(self, log):
        """
        Run portsnap(8) fetch to get an up-to-date ports tree snapshot
        @param log: Open log file
        """
        argv = [PORTSNAP_PATH, 'fetch']
        _runCommand(argv, log, PortsnapCommandError, ROOT_ENV)

    def extract(self, destination, log):
        """
        Run portsnap(8) extract in a ports directory
        @param destination: Ports directory to extract to
        @param log: Open log file
        """
        argv = [PORTSNAP_PATH, '-p', destination, 'extract']
        _runCommand(argv, log, PortsnapCommandError, ROOT_ENV)

class ChflagsCommand(object):
    """
    chflags(1) command context
    """
    def __init__(self, path):
        """
        Create a new ChflagsCommand instance
        @param path: Path to file or directory whose flags will be changed
        """
        self.path = path
    
    def removeAll(self, log):
        """
        Recursively remove all flags from self.path
        @param log: Open log file
        """
        argv = [CHFLAGS_PATH, '-R', '0', self.path]
        _runCommand(argv, log, ChflagsCommandError, ROOT_ENV)

class ChrootCleaner(object):
    """
    Delete a chroot directory completely, then create a new empty directory in 
    its place
    """
    def __init__(self, chroot):
        """
        Create a new ChrootCleaner
        @param chroot Directory that needs to be wiped out
        """
        self.chroot = chroot
    
    def clean(self, log):
        """
        Recursively remove all files from self.chroot
        @param log: Open log file
        """
        if (os.path.exists(self.chroot)):
            log.write("Cleaning out anything in chroot %s\n" % self.chroot)
            # Remove all flags on files in the chroot, then delete it all
            if os.path.exists(self.chroot):
                cc = ChflagsCommand(self.chroot)
                cc.removeAll(log)
                try:
                    shutil.rmtree(self.chroot)
                except Exception, e:
                    raise ChrootCleanerError, "Error cleaning %s: %s" % (self.chroot, e)
        
        # Now create new empty directory
        try:
            os.mkdir(self.chroot)
        except Exception, e:
            raise ChrootCleanerError, "Could not create new chroot directory %s: %s" % (self.chroot, e)

class ReleaseBuilder(object):
    makeTarget = ('release',)
    defaultMakeOptions = {
        'NOPORTS' : 'no',
        'NODOC' : 'no'
    }

    """
    Build a FreeBSD Release
    """
    def __init__(self, cvsroot, cvstag, chroot, makecds=False):
        """
        Create a new ReleaseBuilder instance.

        @param cvsroot: Path to FreeBSD CVS Repository
        @param cvstag: FreeBSD Release Tag
        @param chroot: chroot build directory
        @param makecds: Boolean enables the creation of ISO CD installation images.
        """
        self.cvsroot = cvsroot
        self.cvstag = cvstag
        self.chroot = chroot
        self.makecds = makecds

    def _getBuildName(self, log):
        """
        Extracts the release build name from a copy of newvers.sh written by
        cvs(1) to stdout.
        @param log: Open log file
        @return A string containing the FreeBSD revision and branch connected 
            with a -, e.g. 6.0-RELEASE-p4
        """
        shVarRegex = re.compile(r'^([A-Za-z]+)="([A-Za-z0-9\.\-]+)"')
        fbsdRevision = None
        fbsdBranch = None
        
        argv = [CVS_PATH, '-R', '-d', self.cvsroot, 'co', '-p', '-r', self.cvstag, NEWVERS_PATH]
        buffer = _runCommand(argv, log, CVSCommandError, ROOT_ENV, True)
        
        # Split the input into lines
        lines = buffer.split('\n')

        # Search for the revision and branch variables
        for line in lines:
            vmatch = re.search(shVarRegex, line)
            if (vmatch):
                if (vmatch.group(1) == 'REVISION'):
                    fbsdRevision = vmatch.group(2)
                elif (vmatch.group(1) == 'BRANCH'):
                    fbsdBranch = vmatch.group(2)
        
        if (not fbsdRevision or not fbsdBranch):
            raise NCVSParseError
        
        return fbsdRevision + '-' + fbsdBranch

    def build(self, log):
        """
        Build the release
        @param log: Open log file
        """
        # Grab the correct buildname from CVS
        try:
            buildname = self._getBuildName(log)
        except CVSCommandError, e:
            raise ReleaseBuildError, "An error occurred with cvs while trying to find release name to build: %s" % (e)
        except NCVSParseError, e:
            raise ReleaseBuildError, "Could not parse build name from newvers.sh in cvs repository \"%s\" while building release" % (self.cvsroot)
        
        makeOptions = self.defaultMakeOptions.copy()
        makeOptions['CHROOTDIR'] = self.chroot
        makeOptions['CVSROOT'] = self.cvsroot
        makeOptions['RELEASETAG'] = self.cvstag
        makeOptions['BUILDNAME'] = buildname
        if (self.makecds == True):
            makeOptions['MAKE_ISOS'] = 'yes'
        
        # Then try to run make
        try:
            makecmd = MakeCommand(FREEBSD_REL_PATH, self.makeTarget, makeOptions)
            makecmd.make(log)
        except MakeCommandError, e:
            raise ReleaseBuildError, "An error with make occurred while building the release: %s" % (e)

class ISOReader(object):
    """
    Copy a binary FreeBSD release from a mounted CD image into a build chroot's
    RELEASE_CD_PATH. 
    """
    def __init__(self, mountpoint, releaseroot):
        """
        Create a new ISOReader instance
        @param mountpoint: Mount point of FreeBSD install ISO
        @param releaseroot Release directory to copy the release to. The full 
            contents of the ISO are copied to RELEASE_CD_PATH in this directory
        """
        self.mountpoint = mountpoint
        self.releaseroot = releaseroot
        self.cdroot = os.path.join(self.releaseroot, RELEASE_CD_PATH)
    
    def copy(self, log):
        """
        Copy release from ISO to target directory.
        @param log: Open log file
        """
        # Clean out release
        try:
            cc = ChrootCleaner(self.releaseroot)
            cc.clean(log)
        except ChrootCleanerError, e:
            raise ISOReaderError, "Error cleaning chroot %s: %s" % (self.releaseroot, e)

        # Now do the copy
        try:
            utils.copyRecursive(self.mountpoint, self.cdroot, symlinks=True)
        except utils.Error, e:
            raise ISOReaderError, "Error copying contents of ISO at %s to %s: %s" % (self.mountpoint, self.cdroot, e)

class PackageChrootAssembler(object):
    """
    Extract release binaries into a chroot in which packages can be built.
    """
    def __init__(self, releaseroot, chroot):
        """
        Create a new PackageChrootAssembler instance
        @param releaseroot: Directory that contains built release in R/
        @param chroot: Chroot directory to install to
        """
        self.cdroot = os.path.join(releaseroot, RELEASE_CD_PATH)
        self.chroot = chroot
    
    def _extractDist(self, distdir, distname, target, log):
        log.write("Extracting dist %s from %s to %s\n" % (distname, distdir, target))
        # Create target directory if it isn't already there
        if (not os.path.exists(target)):
            os.makedirs(target)
        
        # Extract a distribution set into the chroot with tar. We use the 
        # subprocess module directly here rather than the helper function 
        # _runCommand so we will have control over the process' standard input.
        argv = [TAR_PATH, '--unlink', '-xpvzf', '-', '-C', target]
        proc = subprocess.Popen(argv, stdout=log, stderr=log, env=ROOT_ENV, stdin=subprocess.PIPE)
        
        path = os.path.join(distdir, distname)
        files = glob.glob(path + '.??')
        for filename in files:
            file = open(filename, 'rb')
            proc.stdin.write(file.read())
            file.close()
        
        proc.stdin.close()
        retval = proc.wait()
        if retval != 0:
            raise TarCommandError, "%s returned with exit code %d while extracting dist %s" % (argv[0], retval, distname)
        
    def _extractAll(self, dists, log):
        # Extract each dist in the chroot
        for key in dists.iterkeys():
            distdir = os.path.join(self.cdroot, os.path.join(self.cdroot, _getCDRelease(self.cdroot)), key)
            for distname in dists[key]:
                # Just to make things difficult, not all dists extract
                # relative to /. TODO: I'd love to handle this without hard 
                # coding. The only place I see the relative path these
                # distribution sets get extracted to is in the Distribution
                # structs near the top of /usr/src/usr.sbin/sysinstall/dist.c. 
                # Hopefully this does not change too much from release to 
                # release.
                if key == 'src':
                    target = os.path.join(self.chroot, 'usr', 'src')
                elif key == 'kernels':
                    target = os.path.join(self.chroot, 'boot')
                else:
                    target = self.chroot
            
                self._extractDist(distdir, distname, target, log)
    
    def extract(self, dists, log):
        """
        Extract the release into a chroot
        @param dists: Dictionary of distribution sets to extract. The key is a 
            string corresponding to the name of the dist, and the value is an 
            array of the subdists in that directory. For dists that don't have 
            a lot of subdists, this value will just be an array containing the 
            same string as the key.
        @param log: Open log file
        """
        # Clean out chroot
        try:
            cc = ChrootCleaner(self.chroot)
            cc.clean(log)
        except ChrootCleanerError, e:
            raise PackageChrootAssemblerError, "Error cleaning chroot %s: %s" % (self.chroot, e)
        
        # Then extract all dists and add /etc/resolv.conf to chroot
        try:
            self._extractAll(dists, log)
            utils.copyWithOwnership(os.path.join(ROOT_PATH, RESOLV_CONF), os.path.join(self.chroot, RESOLV_CONF))
        except Exception, e:
            raise PackageChrootAssemblerError, "Error populating chroot %s: %s" % (self.chroot, e)

class PackageBuilder(object):
    """
    Build a package from a FreeBSD port
    """
    makeTarget = ('deinstall', 'clean', 'package-recursive')
    defaultMakeOptions = {
        'PACKAGE_BUILDING'  : 'yes',
        'BATCH'             : 'yes',
        'NOCLEANDEPENDS'    : 'yes'
    }

    """
    Build a FreeBSD Package 
    """
    def __init__(self, pkgroot, port, buildOptions=None):
        """
        Create a new PackageBuilder instance.

        @param pkgroot: Chroot directory where packages will be built
        @param port: Port to build
        @param buildOptions: Build options for the package
        """
        self.pkgroot = pkgroot
        self.port = port
        self.buildOptions = buildOptions

    def build(self, log):
        """
        Build the package 
        @param log: Open log file
        """
        makeOptions = self.defaultMakeOptions.copy()
        makeOptions.update(self.buildOptions)
        makecmd = MakeCommand(os.path.join(FREEBSD_PORTS_PATH, self.port), self.makeTarget, makeOptions, self.pkgroot)
        try:
            makecmd.make(log)
        except MakeCommandError, e:
            raise PackageBuildError, "An error occured building the port \"%s\": %s" % (self.port, e)

class InstallAssembler(object):
    """
    Assemble an installation configuration
    """
    def __init__(self, name, description, releaseroot, installConfigPath):
        """
        @param name: A unique name for this install instance 
        @param description: A human-readable description of this install type
        @param releaseroot: Directory containing the release binaries
        @param installConfigFile: The complete path to this installation's install.cfg
        """
        self.name = name
        self.description = description
        self.releaseroot = releaseroot
        self.installConfigSource = installConfigPath
        
        #
        # Source Paths
        #
        
        # Contains shared release boot files
        self.bootRoot = os.path.join(self.releaseroot, RELEASE_CD_PATH, 'boot')
        # Shared release mfsroot
        self.mfsCompressed = os.path.join(self.bootRoot, 'mfsroot.gz')
        # Directory containing generic kernel and its modules
        self.kernel = os.path.join(self.bootRoot, 'kernel')

    def _decompressMFSRoot(self, mfsOutput):
        """
        Decompression/writing of mfsroot file
        """
        compressedFile = gzip.GzipFile(self.mfsCompressed, 'rb')
        outputFile = open(mfsOutput, 'wb')
        while (True):
            data = compressedFile.read(1024)
            if (not data):
                break
            outputFile.write(data)
    
    def _mountMFSRoot(self, mfsOutput, mountPoint, log):
        """
        Once the MFS root has been decompressed, mount it
        """
        mdconfig = MDConfigCommand(mfsOutput)
        # Create the mount point, if necessary
        if (not os.path.exists(mountPoint)):
            os.mkdir(mountPoint)
        self.mdmount = MDMountCommand(mdconfig, mountPoint)
        self.mdmount.mount(log)

    def _copyKernel(self, destdir):
        """
        Copy the kernel directory to the install-specific directory
        """
        dest = os.path.join(destdir, 'kernel')
        utils.copyRecursive(self.kernel, dest, symlinks=True)

    def _doWriteBootConf(self, destdir):
        """
        Write the per-install bootloader configuration file
        """
        subst = {}
        subst['bootdir'] = os.path.basename(destdir)

        output = open(os.path.join(destdir, 'boot.conf'), 'w')
        template = open(farb.BOOT_CONF_TMPL, 'r')

        for line in template:
            output.write(line % (subst))

        output.close()
        template.close()
        
    def build(self, destdir, log):
        """
        Build the MFSRoot, build the boot loader configuration, and copy the kernel.
        @param destdir: The installation-specific boot-loader directory
        @param log: Open log file
        """

        #
        # Destination Paths
        #
        # Path to installation-specific mfsroot
        mfsOutput = os.path.join(destdir, "mfsroot")
        # Temporary mount point for the mfsroot image
        mountPoint = os.path.join(destdir, "mnt")
        # Write the install.cfg to the mfsroot mount point
        installConfigDest = os.path.join(mountPoint, 'install.cfg')

        try:
            # Create the destdir, if necessary
            if (not os.path.exists(destdir)):
                os.mkdir(destdir)

            # Write the uncompressed mfsroot file
            log.write("Decompressing %s to %s\n" % (self.mfsCompressed, mfsOutput))
            self._decompressMFSRoot(mfsOutput)
        
            # Mount the mfsroot once it has been decompressed
            log.write("Mounting %s on %s\n" % (mfsOutput, mountPoint))
            self._mountMFSRoot(mfsOutput, mountPoint, log)

            # Copy the install.cfg to the attached md device
            log.write("Copying %s to mfsroot mounted at %s\n" % (self.installConfigSource, mountPoint))
            shutil.copy2(self.installConfigSource, installConfigDest)

            # Unmount/detach md device
            self.mdmount.umount(log)

            # Copy the kernel
            log.write("Copying kernel from %s to %s\n" % (self.kernel, destdir))
            self._copyKernel(destdir)

            # Write boot.conf
            log.write("Writing out boot.conf file in %s\n" % destdir)
            self._doWriteBootConf(destdir)
        
        except MDConfigCommandError, e:
            raise InstallAssembleError, "An error occured operating on the mfsroot \"%s\": %s" % (self.mfsOutput, e)
        except MountCommandError, e:
            raise InstallAssembleError, "An error occured mounting \"%s\": %s" % (self.mfsOutput, e)
        except exceptions.IOError, e:
            raise InstallAssembleError, "An I/O error occured: %s" % e
        except Exception, e:
            raise InstallAssembleError, "An error occured: %s" % e

class ReleaseAssembler(object):
    """
    Assemble the per-release installation data directory.
    """
    def __init__(self, name, releaseroot, pkgroot, localData = []):
        """
        Initialize the ReleaseAssembler
        @param name: A unique name for this release
        @param releaseroot: Directory containing the release binaries
        @param pkgroot: Chroot directory where packages were built
        @param localData: List of file and directory paths to copy to installRoot/local.
        """
        self.name = name
        self.cdroot = os.path.join(releaseroot, RELEASE_CD_PATH)
        self.pkgroot = pkgroot
        self.localData = localData

    def build(self, destdir, log):
        """
        Create the install root, copy in the release data,
        write out the bootloader configuration and kernels.
        @param destdir: Per-release installation data directory.
        @param log: Open log file.
        """
        try:
            # Copy the installation data
            log.write("Copying release files from %s to %s\n" % (os.path.join(self.cdroot, _getCDRelease(self.cdroot)), destdir))
            utils.copyRecursive(os.path.join(self.cdroot, _getCDRelease(self.cdroot)), destdir, symlinks=True)

            # If there are packages, copy those too
            packagedir = os.path.join(self.pkgroot, RELEASE_PACKAGE_PATH)
            log.write("Copying packages from %s to %s\n" % (packagedir, os.path.join(destdir, 'packages')))
            if (os.path.exists(packagedir)):
                utils.copyRecursive(packagedir, os.path.join(destdir, 'packages'), symlinks=True)

            # Copy in any local data
            if (len(self.localData)):
                # Create the local directory
                localdir = os.path.join(destdir, 'local')
                os.mkdir(localdir)

                for path in self.localData:
                    log.write("Copying extra local data from %s to %s\n" % (path, os.path.join(localdir, os.path.basename(path))))
                    if (os.path.isdir(path)):
                        utils.copyRecursive(path, os.path.join(localdir, os.path.basename(path)), symlinks=True)
                    else:
                        utils.copyWithOwnership(path, localdir)

            # Add the FarBot package installer script and make it executable
            log.write("Installing package installer script to %s\n" % destdir)
            utils.copyWithOwnership(farb.INSTALL_PACKAGE_SH, destdir)
            os.chmod(os.path.join(destdir, os.path.basename(farb.INSTALL_PACKAGE_SH)), 0755)
        except exceptions.IOError, e:
            raise ReleaseAssembleError, "An I/O error occured: %s" % e
        except Exception, e:
            raise ReleaseAssembleError, "An error occured: %s" % e

class NetInstallAssembler(object):
    """
    Assemble the netinstall directory, including the tftproot,
    using the supplied release and install assemblers.
    """
    def __init__(self, installroot, releaseAssemblers, installAssemblers):
        """
        Initialize the InstallRootBuilder
        @param installroot: Network install/boot directory.
        @param releaseAssemblers: List of ReleaseAssembler instances.
        @param installAssemblers: List of InstallAssembler instances.
        """
        self.installroot = installroot
        self.tftproot = os.path.join(installroot, 'tftproot')
        self.releaseAssemblers = releaseAssemblers
        self.installAssemblers = installAssemblers

    def _doConfigureBootLoader(self, destdir):
        """
        Write out the forth for the boot loader installation menu
        """
        subst = {}

        # Format Strings
        variableFormat = 'variable %s\n'
        menuItemFormat = 'printmenuitem ."  %s" %s !\n'
        ifBlockFormat = 'dup %s @ = if\ns" /%s/boot.conf" read-conf\n0 boot-conf exit\nthen\n'

        # Output
        variables = cStringIO.StringIO()
        menuItems = cStringIO.StringIO()
        ifBlocks = cStringIO.StringIO()

        # Generate the code blocks
        for install in self.installAssemblers:
            # Variable declaration
            variableName = install.name + '_key'
            variables.write(variableFormat % (variableName))

            # Menu item
            menuItems.write(menuItemFormat % (install.description, variableName))

            # if block
            ifBlocks.write(ifBlockFormat % (variableName, install.name))

        # Write out the netinstall.4th file
        subst['variables'] = variables.getvalue()
        subst['menuitems'] = menuItems.getvalue()
        subst['ifblocks'] = ifBlocks.getvalue()
        output = open(os.path.join(destdir, 'netinstall.4th'), 'w')
        template = open(farb.NETINSTALL_FORTH_TMPL, 'r')

        for line in template:
            output.write(line % (subst))

        output.close()
        template.close()

        # Copy in our loader.conf and loader.rc
        utils.copyWithOwnership(farb.LOADER_CONF, destdir)
        utils.copyWithOwnership(farb.LOADER_RC, destdir)

    def build(self, log):
        """
        Create the install root, copy in the release data,
        write out the bootloader configuration and kernels.
        @param log: Open log file.
        """
        try:
            # Create the installation root, if necessary
            if (not os.path.exists(self.installroot)):
                os.mkdir(self.installroot)

            # Create the tftproot, if necessary
            if (not os.path.exists(self.tftproot)):
                os.mkdir(self.tftproot)

            # Copy over the shared boot loader and kernel. Lacking any better heuristic, we
            # grab the boot loader from the first release provided -- shouldn't
            # matter where we get it, really. However, there are some differences between
            # where releases store the generic kernel, so we try to impedence match.
            release = self.releaseAssemblers[0]
            source = os.path.join(release.cdroot, 'boot')
            dest = os.path.join(self.tftproot, os.path.basename(source))

            # Copy it
            log.write("Copying shared boot loader and kernel from %s to %s\n" % (source, dest))
            utils.copyRecursive(source, dest, symlinks=True)

            # Configure it
            log.write("Generating netinstall.4th and copying loader.conf and loader.rc to %s\n" % dest)
            self._doConfigureBootLoader(dest)

            # Assemble the release data
            for release in self.releaseAssemblers:
                destdir = os.path.join(self.installroot, release.name)
                log.write("Assembling release data in %s\n" % destdir)
                release.build(destdir, log)

            # Assemble the installation data
            for install in self.installAssemblers:
                destdir = os.path.join(self.tftproot, install.name)
                log.write("Assembling installation-specific data in %s\n" % destdir)
                install.build(destdir, log)

        except exceptions.IOError, e:
            raise NetInstallAssembleError, "An I/O error occured: %s" % e
        except exceptions.OSError, e:
            raise NetInstallAssembleError, "An OS error occured: %s" % e
        except Exception, e:
            raise NetInstallAssembleError, "An error occured: %s" % e

def _getCDRelease(cdroot):
    # Get the release name from the cdrom.inf file in cdroot
    infFile = os.path.join(cdroot, 'cdrom.inf')
    if not os.path.exists(infFile):
        raise CDReleaseError, "No cdrom.inf file in %s. Is this a disc 1 root directory for FreeBSD >= 2.1.5?" % (cdroot)

    # First line in cdrom.inf should look like: CD_VERSION = x.y-RELEASE
    fileObj = open(infFile, 'r')
    line = fileObj.readline()
    fileObj.close()

    line = line.strip()
    splitString = line.split(' = ')
    if (len(splitString) != 2 or splitString[0] != 'CD_VERSION'):
        raise CDReleaseError, "cdrom.inf file in %s has unrecognized first line: %s" % (cdroot, line)

    return splitString[1]

def _runCommand(argv, log, exception, env=ROOT_ENV, returnOut=False):
    """
    Run a command, logging its output to an open file. Raise an exception if it 
    has an exit code of anything other than 0.
    @param argv: List containing path of command, followed by its arguments
    @param log: Open log file where stderr and possibly stdout will be written.
    @param exception: Type of exception to throw if command returns a value 
        other than zero
    @param env: Dictionary of the environment to run the command under. Defaults 
        to ROOT_ENV
    @param returnOut: If true, instead of writing stderr to the file log, the 
        contents of the commands output will be returned by this function. 
        Defaults to false.
    @return A string containing what the command prints to stdout if returnOut 
        is true. None otherwise.
    """
    if returnOut:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=log, env=env)
    else:
        process = subprocess.Popen(argv, stdout=log, stderr=log, env=env)
    
    retval = process.wait()
    
    # Read all of what the command wrote to stdout if we set returnOut
    outputString = None
    if returnOut:
        outputString = process.stdout.read()
        
    if retval != 0:
        raise exception, "Command %s returned with exit code %d" % (argv[0], retval)
    
    return outputString
