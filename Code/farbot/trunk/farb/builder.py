# builder.py vi:ts=4:sw=4:expandtab:
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

from twisted.internet import reactor, defer, protocol, threads
from twisted.python import threadable
threadable.init()

import os, re, gzip, shutil, exceptions
import cStringIO

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

# Standard FreeBSD src location
FREEBSD_REL_PATH = '/usr/src/release'

# Standard FreeBSD ports location
FREEBSD_PORTS_PATH = '/usr/ports'

# Relative path of newvers.sh file in the FreeBSD CVS repository
NEWVERS_PATH = 'src/sys/conf/newvers.sh'

# Release-relative path to the boot directory
RELEASE_BOOT_PATH = 'R/stage/trees/base/boot'

# Release-relative path to the package directory
RELEASE_PACKAGE_PATH = 'usr/ports/packages'

# Release-relative path to the ftp installation data directory
RELEASE_FTP_PATH = 'R/ftp'

# Release-relative path to the mfsroot directory
RELEASE_MFSROOT_PATH = 'R/stage/mfsroot'

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

class ReleaseBuildError(farb.FarbError):
    pass

class PackageBuildError(farb.FarbError):
    pass

class InstallAssembleError(farb.FarbError):
    pass

class ReleaseAssembleError(farb.FarbError):
    pass

class NetinstallAssembleError(farb.FarbError):
    pass

class LoggingProcessProtocol(protocol.ProcessProtocol):
    """
    make(1) process protocol
    """
    def __init__(self, deferred, log):
        """
        @param deferred: Deferred to call with process return code
        @param log: Open log file
        """
        self.log = log
        self.d = deferred

    def outReceived(self, data):
        self.log.write(data)

    def errReceived(self, data):
        self.log.write(data)

    def connectionMade(self):
        # We're not interested in writing to stdin
        self.transport.closeStdin()

    def processEnded(self, status):
        if (status.value.exitCode == 0):
            self.d.callback(status.value.exitCode)
        else:
            self.d.errback(CommandError(status.value.exitCode))


class NCVSBuildnameProcessProtocol(protocol.ProcessProtocol):
    """
    FreeBSD CVS newvers.sh information extraction.

    Extracts the release build name from a copy of newvers.sh written by
    cvs(1) to stdout.
    """
    _buffer = ''
    delimiter = '\n'

    def __init__(self, deferred):
        """
        @param deferred: Deferred to call with process return code
        """
        self.d = deferred
        self.shVarRegex = re.compile(r'^([A-Za-z]+)="([A-Za-z0-9\.\-]+)"')
        self.fbsdRevision = None
        self.fbsdBranch = None

    def outReceived(self, data):
        """
        Searches a shell script for lines matching VARIABLE=VALUE, 
        looking for the FreeBSD revision and branch variable assignments
        Uses line-oriented input buffering.
        """
        # Split the input into lines
        lines = (self._buffer + data).split(self.delimiter)
        # Pop the last (potentially incomplete) line
        self._buffer = lines.pop(-1)

        # Search for the revision and branch variables
        for line in lines:
            vmatch = re.search(self.shVarRegex, line)
            if (vmatch):
                if (vmatch.group(1) == 'REVISION'):
                    self.fbsdRevision = vmatch.group(2)
                elif (vmatch.group(1) == 'BRANCH'):
                    self.fbsdBranch = vmatch.group(2)

    def processEnded(self, status):
        if (status.value.exitCode != 0):
            self.d.errback(CVSCommandError('cvs(1) returned %d' % status.value.exitCode))
            return

        if (not self.fbsdRevision or not self.fbsdBranch):
            self.d.errback(NCVSParseError('Could not parse both REVISION and BRANCH variables'))
            return

        self.d.callback(self.fbsdRevision+ '-' + self.fbsdBranch)

class MDConfigProcessProtocol(protocol.ProcessProtocol):
    """
    FreeBSD mdconfig(1) protocol.
    Attach and detach vnode md(4) devices.
    """
    _buffer = ''

    def __init__(self, deferred):
        """
        @param deferred: Deferred to call with process return code
        """
        self.d = deferred

    def outReceived(self, data):
        """
        mdconfig(1) will output the md(4) device name
        """
        self._buffer = self._buffer.join(data)

    def processEnded(self, status):
        if (status.value.exitCode != 0):
            self.d.errback(MDConfigCommandError('mdconfig returned %d' % status.value.exitCode))
            return

        self.d.callback(self._buffer.rstrip('\n'))

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

    def _cbAttached(self, result):
        self.md = result

    def attach(self):
        """
        Attach the file to an md(4) device
        """
        assert(self.md == None)

        # Create command argv
        argv = [MDCONFIG_PATH, '-a', '-t', 'vnode', '-f', self.file]
        d = defer.Deferred()
        protocol = MDConfigProcessProtocol(d)
        reactor.spawnProcess(protocol, MDCONFIG_PATH, args=argv, env=ROOT_ENV)
        d.addCallback(self._cbAttached)

        return d

    def detach(self):
        """
        Attach the file to an md(4) device
        """
        assert(self.md)

        # Create command argv
        argv = [MDCONFIG_PATH, '-d', '-u', self.md]
        d = defer.Deferred()
        protocol = MDConfigProcessProtocol(d)
        reactor.spawnProcess(protocol, MDCONFIG_PATH, args=argv, env=ROOT_ENV)

        return d

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

    def _ebCVS(self, failure):
        # Provide a more specific exception type
        failure.trap(CommandError)
        raise CVSCommandError, failure.value

    def export(self, release, module, destination, log):
        """
        Run cvs(1) export
        @param release: release to checkout, ex. HEAD 
        @param module: module to use, ex: ports 
        @param destination: destination for the export 
        @param log: Open log file
        """

        # Create command argv
        d = defer.Deferred()
        d.addErrback(self._ebCVS)
        protocol = LoggingProcessProtocol(d, log)
        argv = [CVS_PATH, '-R', '-d', self.repository, 'export', '-r', release, '-d', destination, module]

        reactor.spawnProcess(protocol, CVS_PATH, args=argv, env=ROOT_ENV)

        return d

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


    def _ebMount(self, failure):
        # Provide a more specific exception type
        failure.trap(CommandError)
        raise MountCommandError, failure.value

    def mount(self, log):
        """
        Run mount(8)
        @param log: Open log file
        """

        # Create command argv
        d = defer.Deferred()
        d.addErrback(self._ebMount)
        protocol = LoggingProcessProtocol(d, log)
        if (self.fstype):
            argv = [MOUNT_PATH, '-t', self.fstype, self.device, self.mountpoint]
        else:
            argv = [MOUNT_PATH, self.device, self.mountpoint]

        reactor.spawnProcess(protocol, MOUNT_PATH, args=argv, env=ROOT_ENV)

        return d

    def umount(self, log):
        """
        Run umount(8)
        @param log: Open log file
        """

        # Create command argv
        d = defer.Deferred()
        d.addErrback(self._ebMount)
        protocol = LoggingProcessProtocol(d, log)
        argv = [UMOUNT_PATH, self.mountpoint]

        reactor.spawnProcess(protocol, UMOUNT_PATH, args=argv, env=ROOT_ENV)

        return d

class MDMountCommand(MountCommand):
    """
    mount(8)/umount(8) command context
    """
    def __init__(self, mdc, mountpoint):
        """
        Create a new MountCommand instance
        @param mdc: MDConfigCommand instance
        @param mountpoint: mount point
        """
        self.mdc = mdc
        super(MDMountCommand, self).__init__(None, mountpoint)

    def _ebUnmount(self, failure):
        # Provide a more specific exception type
        failure.trap(CommandError)
        raise MountCommandError, failure.value

    def _cbUnmount(self, result):
        """
        Device unmounted, detach it
        """
        d = self.mdc.detach()
        d.addCallback(self._cbDetach, result)

        return d

    def _cbAttach(self, result, log):
        """
        Device attached, mount it
        """
        # build the device path
        self.device = os.path.join('/dev/', self.mdc.md)
        return super(MDMountCommand, self).mount(log)

    def _cbDetach(self, result, mountExitCode):
        # Return the mount(8) exit code
        return mountExitCode

    def mount(self, log):
        """
        Attach the device, run mount(8)
        @param log: Open log file
        """

        # Attach the image. Let the caller
        # handle MDConfigCommand exceptions
        # directly
        d = self.mdc.attach()
        d.addCallback(self._cbAttach, log)

        return d

    def umount(self, log):
        """
        Run unmount(8), detach the image.
        @param log: Open log file
        """

        # Unmount the image, detach it on success.
        #
        # Clean up the CommandError exception
        # on failure.
        d = super(MDMountCommand, self).umount(log)
        d.addCallbacks(self._cbUnmount, self._ebUnmount)

        return d


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

    def _ebMake(self, failure):
        # Provide a more specific exception type
        failure.trap(CommandError)
        raise MakeCommandError, failure.value

    def make(self, log):
        """
        Run make(1)
        @param log: Open log file
        """

        # Create command argv
        d = defer.Deferred()
        d.addErrback(self._ebMake)
        protocol = LoggingProcessProtocol(d, log)
        argv = [MAKE_PATH, '-C', self.directory]
        if self.chrootdir:
            runCmd = CHROOT_PATH
            argv.insert(0, self.chrootdir)
            argv.insert(0, CHROOT_PATH)
        else:
            runCmd = MAKE_PATH

        for target in self.targets:
            argv.append(target)

        for option, value in self.options.items():
            argv.append("%s=%s" % (option, value))
        reactor.spawnProcess(protocol, runCmd, args=argv, env=ROOT_ENV)

        return d


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

    def _ebBuildError(self, failure):
        try:
            failure.raiseException()
        except CVSCommandError, e:
            raise ReleaseBuildError, "An error occured extracting the release name from \"%s\": %s" % (self.cvsroot, e)
        except MakeCommandError, e:
            raise ReleaseBuildError, "An error occured building the release, make command returned: %s" % (e)

    def _doBuild(self, buildname, log):
        makeOptions = self.defaultMakeOptions.copy()
        makeOptions['CHROOTDIR'] = self.chroot
        makeOptions['CVSROOT'] = self.cvsroot
        makeOptions['RELEASETAG'] = self.cvstag
        makeOptions['BUILDNAME'] = buildname

        if (self.makecds == True):
            makeOptions['MAKE_ISOS'] = 'yes'

        makecmd = MakeCommand(FREEBSD_REL_PATH, self.makeTarget, makeOptions)
        d = makecmd.make(log)

        return d

    def build(self, log):
        """
        Build the release
        @param log: Open log file
        @return Returns a deferred that will be called when make(1) completes
        """

        # Grab the correct buildname from CVS
        d = defer.Deferred()
        pp = NCVSBuildnameProcessProtocol(d)

        # Kick off the build once we get the release name from CVS
        d.addCallback(self._doBuild, log)
        d.addErrback(self._ebBuildError)
        reactor.spawnProcess(pp, CVS_PATH, args=[CVS_PATH, '-R', '-d', self.cvsroot, 'co', '-p', '-r', self.cvstag, NEWVERS_PATH], env=ROOT_ENV)
        return d

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
    def __init__(self, chroot, port, buildOptions=None):
        """
        Create a new PackageBuilder instance.

        @param chroot: Release chroot directory
        @param port: Port to build
        @param buildOptions: Build options for the package
        """
        self.chroot = chroot
        self.port = port
        self.buildOptions = buildOptions

    def _ebBuildError(self, failure):
        try:
            failure.raiseException()
        except MakeCommandError, e:
            raise PackageBuildError, "An error occured building the port \"%s\", make command returned: %s" % (self.port, e)

    def build(self, log):
        """
        Build the package 
        @param log: Open log file
        @return Returns a deferred that will be called when make(1) completes
        """

        # Load up a deferred with the right call backs and return it
        # ready to be spawned
        makeOptions = self.defaultMakeOptions.copy()
        makeOptions.update(self.buildOptions)
        makecmd = MakeCommand(os.path.join(FREEBSD_PORTS_PATH, self.port), self.makeTarget, makeOptions, self.chroot)
        d = makecmd.make(log)
        d.addErrback(self._ebBuildError)
        return d

class InstallAssembler(object):
    """
    Assemble an installation configuration
    """
    def __init__(self, name, description, chroot, installConfigPath):
        """
        @param name: A unique name for this install instance 
        @param description: A human-readable description of this install type
        @param chroot: The chroot for this release
        @param installConfigFile: The complete path to this installation's install.cfg
        """
        self.name = name
        self.description = description
        self.chroot = chroot
        self.installConfigSource = installConfigPath
        
        #
        # Source Paths
        #
        
        # Contains shared release boot files
        self.bootRoot = os.path.join(self.chroot, RELEASE_BOOT_PATH)
        # Per-release source path for the kernel and modules
        self.kernel = os.path.join(self.bootRoot, 'kernel')
        # Shared release mfsroot
        self.mfsCompressed = os.path.join(self.chroot, RELEASE_MFSROOT_PATH, 'mfsroot.gz')
        
    def _ebInstallError(self, failure):
        try:
            failure.raiseException()
        except MDConfigCommandError, e:
            raise InstallAssembleError, "An error occured operating on the mfsroot \"%s\": %s" % (self.mfsOutput, e)
        except MountCommandError, e:
            raise InstallAssembleError, "An error occured mounting \"%s\": %s" % (self.mfsOutput, e)
        except exceptions.IOError, e:
            raise InstallAssembleError, "An I/O error occured: %s" % e
        except Exception, e:
            raise InstallAssembleError, "An error occured: %s" % e

    def _decompressMFSRoot(self, mfsOutput):
    	"""
    	Synchronous decompression/writing of mfsroot file
    	(Not worth making async, so run in a thread)
    	"""
    	compressedFile = gzip.GzipFile(self.mfsCompressed, 'rb')
    	outputFile = open(mfsOutput, 'wb')
    	while (True):
    		data = compressedFile.read(1024)
    		if (not data):
    			break
    		outputFile.write(data)

        return mfsOutput

    def _cbMountMFSRoot(self, mfsOutput, mountPoint, log):
    	"""
    	Once the MFS root has been decompressed,
    	mount it
    	"""
    	mdconfig = MDConfigCommand(mfsOutput)
    	# Create the mount point, if necessary
    	if (not os.path.exists(mountPoint)):
    		os.mkdir(mountPoint)
    	self.mdmount = MDMountCommand(mdconfig, mountPoint)
    	return self.mdmount.mount(log)

    def _cbCopyKernel(self, result, destdir):
        """
        Copy the kernel directory to the install-specific directory
        (Synchronous)
        """
        dest = os.path.join(destdir, os.path.basename(self.kernel))
        d = threads.deferToThread(utils.copyRecursive, self.kernel, dest, symlinks=True)
        return d

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
        @return Returns a deferred
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

        # Create the destdir, if necessary
        if (not os.path.exists(destdir)):
            os.mkdir(destdir)

        # Write the uncompressed mfsroot file
        d = threads.deferToThread(self._decompressMFSRoot, mfsOutput)
        # Mount the mfsroot once it has been decompressed
        d.addErrback(self._ebInstallError)
        d.addCallback(self._cbMountMFSRoot, mountPoint, log)

        # Copy the install.cfg to the attached md device
        d.addCallback(lambda _: defer.execute(shutil.copy2, self.installConfigSource, installConfigDest))

        # Unmount/detach md device
        d.addCallback(lambda _: self.mdmount.umount(log))

        # Copy the kernel
        d.addCallback(self._cbCopyKernel, destdir)

        # Write boot.conf
        d.addCallback(lambda _: threads.deferToThread(self._doWriteBootConf, destdir))
        
        return d


class ReleaseAssembler(object):
    """
    Assemble the per-release installation data directory.
    """
    def __init__(self, name, chroot, localData = []):
        """
        Initialize the ReleaseAssembler
        @param name: A unique name for this release
        @param chroot: The release build chroot
        @param localData: List of file and directory paths to copy to installRoot/local.
        """
        self.name = name
        self.chroot = chroot
        self.localData = localData

    def _cbCopyLocal(self, result, source, dest):
        if (os.path.isdir(source)):
            d = threads.deferToThread(utils.copyRecursive, source, os.path.join(dest, os.path.basename(source)), symlinks=True)
        else:
            d = threads.deferToThread(utils.copyWithOwnership, source, dest)

        return d

    def _ebBuild(self, failure):
        try:
            failure.raiseException()
        except exceptions.IOError, e:
            raise ReleaseAssembleError, "An I/O error occured: %s" % e
        except Exception, e:
            raise ReleaseAssembleError, "An error occured: %s" % e

    def build(self, destdir, log):
        """
        Create the install root, copy in the release data,
        write out the bootloader configuration and kernels.
        @param destdir: Per-release installation data directory.
        @param log: Open log file.
        """
        # Copy the installation data
        d = threads.deferToThread(utils.copyRecursive, os.path.join(self.chroot, RELEASE_FTP_PATH), destdir, symlinks=True)

        # If there are packages, copy those too
        packagedir = os.path.join(self.chroot, RELEASE_PACKAGE_PATH)
        if (os.path.exists(packagedir)):
            d.addCallback(lambda _: threads.deferToThread(utils.copyRecursive, packagedir, os.path.join(destdir, 'packages'), symlinks=True))

        # Copy in any local data
        if (len(self.localData)):
            # Create the local directory
            localdir = os.path.join(destdir, 'local')
            d.addCallback(lambda _: defer.execute(os.mkdir, localdir))

            for path in self.localData:
                d.addCallback(self._cbCopyLocal, path, localdir)

        # Add the FarBot package installer script
        d.addCallback(lambda _: threads.deferToThread(utils.copyWithOwnership, farb.INSTALL_PACKAGE_SH, destdir))

        return d

class NetinstallAssembler(object):
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

    def _ebBuild(self, failure):
        """
        Called if any deferred in the DeferredList
        fails. Handles the original exception.
        """
        try:
            failure.value.subFailure.raiseException()
        except exceptions.IOError, e:
            raise NetinstallAssembleError, "An I/O error occured: %s" % e
        except exceptions.OSError, e:
            raise NetinstallAssembleError, "An OS error occured: %s" % e
        except Exception, e:
            raise NetinstallAssembleError, "An error occured: %s" % e

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
        deferreds = []

        # Create the installation root, if necessary
        if (not os.path.exists(self.installroot)):
            os.mkdir(self.installroot)

        # Create the tftproot, if necessary
        if (not os.path.exists(self.tftproot)):
            os.mkdir(self.tftproot)

        # Copy over the shared boot loader. Lacking any better heuristic, we
        # grab the boot loader from the first release provided -- shouldn't
        # matter where we get it, really.
        release = self.releaseAssemblers[0]
        source = os.path.join(release.chroot, RELEASE_BOOT_PATH)
        dest = os.path.join(self.tftproot, os.path.basename(source))

        # Copy it
        d = threads.deferToThread(utils.copyRecursive, source, dest, symlinks=True)
        # Configure it
        d.addCallback(lambda _: threads.deferToThread(self._doConfigureBootLoader, dest))
        deferreds.append(d)

        # Assemble the release data
        for release in self.releaseAssemblers:
            destdir = os.path.join(self.installroot, release.name)

            d = release.build(destdir, log)
            deferreds.append(d)

        # Assemble the installation data
        for install in self.installAssemblers:
            destdir = os.path.join(self.tftproot, install.name)

            d = install.build(destdir, log)
            deferreds.append(d)

        d = defer.DeferredList(deferreds, fireOnOneErrback=True)
        d.addErrback(self._ebBuild)

        return d
