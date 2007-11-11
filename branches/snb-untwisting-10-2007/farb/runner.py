# runner.py vi:ts=4:sw=4:expandtab:
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

import glob
import os
import shutil

import farb
from farb import builder

# Exceptions
class ReleaseBuildRunnerError(farb.FarbError):
    pass

class PackageBuildRunnerError(farb.FarbError):
    pass

class NetInstallAssemblerRunnerError(farb.FarbError):
    pass

class BuildRunner(object):
    """
    BuildRunner abstract superclass.
    """
    def __init__(self, config):
        # Log file object for the current release's runner log
        self.log = None
        # ZConfig instance of a parsed farbot config file
        self.config = config
    
    def _closeLog(self):
        if self.log:
            self.log.close()

class ReleaseBuildRunner(BuildRunner):
    """
    Run a set of release builds
    """
    def __init__(self, config):
        super(ReleaseBuildRunner, self).__init__(config)
        # Used for MDMountCommand instance for the current release
        self.isomount = None
    
    def _copyFromISO(self):
        # Create the ISOs mount point if needed
        mountpoint = os.path.join(release.buildroot, 'mnt')
        if (not os.path.exists(mountpoint)):
            self.log.write("Creating mount point \"%s\" for ISO" % mountpoint)
            os.mkdir(mountpoint)

        # Mount the ISO
        self.log.write("Mount ISO at \"%s\"" % mountpoint)
        mdconfig = builder.MDConfigCommand(release.iso)                
        self.isomount = builder.MDMountCommand(mdconfig, mountpoint, fstype='cd9660')
        self.isomount.mount(buildLog)
    
        # Copy ISO contents to release directory
        self.log.write("Release %s copying to %s" % (release.getSectionName(), release.releaseroot))
        isoReader = builder.ISOReader(mountpoint, release.releaseroot)
        isoReader.copy(self.log)
    
    def run(self):
        # Iterate through all releases, starting a release build for all
        # releases referenced by an Installation.
        for release in self.config.Releases.Release:
            releaseName = release.getSectionName()
            
            # Check all installations for a reference to this release
            for install in config.Installations.Installation:
                releaseFound = False
                if (releaseName == install.release.lower()):
                    releaseFound = True
                    break
            if (not releaseFound):
                # Skip the release, it's not used by any installation
                break

            logPath = os.path.join(release.buildroot, 'build.log')
            try:
                try:
                    # Create the build directory
                    if (not os.path.exists(release.buildroot)):
                        os.makedirs(release.buildroot)
            
                    # Open the build log file
                    self.log = open(logPath, 'w', 0)
            
                    if (release.binaryrelease):
                        self._copyFromISO()
                    else:
                        # Instantiate our builder
                        self.log.write("Starting build of release %s" % releaseName)
                        releaseBuilder = builder.ReleaseBuilder(release.cvsroot, release.cvstag, release.releaseroot, release.installcds)
                        releaseBuilder.build(self.log)
            
                except builder.ReleaseBuildError, e:
                     raise ReleaseBuildRunnerError, "Build of release %s failed: %s\nMore details may be found in %s" % (releaseName, e, logPath)
                except builder.ISOReaderError, e:
                     raise ReleaseBuildRunnerError, "Failed to copy release %s from ISO: %s\nMore details may be found in %s" % (releaseName, e, logPath)
                except Exception, e:
                     raise ReleaseBuildRunnerError, "Unhandled error while building release %s: %s\nMore details may be found in %s" % (releaseName, e, logPath)

            finally:
                # Unmount any ISO and detach its MD device.
                if self.isomount:
                    self.isomount.umount(self.log)
                
                # Close our log file
                self._closeLog()

class PackageBuildRunner(BuildRunner):
    """
    Run a set of package builds
    """
    def __init__(self, config):
        super(PackageBuildRunner, self).__init__()
        self.oe = utils.OrderedExecutor()
        self.devmounts = {}
        self.distfilescache = None
        self.distfilesmounts = {}
        
        if config.PackageSets:
            self.distfilescache = config.PackageSets.distfilescache
        
        # Create the distfiles cache directory if necessary
        try:
            if (self.distfilescache and not os.path.exists(self.distfilescache)):
                os.makedirs(self.distfilescache)
        except Exception, e:
            print "Failed to create distfiles cache directory %s: %s" % (self.distfilescache, e)
            sys.exit(1)

        # Iterate through all releases, starting a package build for all
        # listed packages
        for release in config.Releases.Release:
            # Grab the list of packages provided by verifyPackages()
            if (not release.packages):
                continue

            # Open a packaging log file
            logPath = os.path.join(release.buildroot, 'packaging.log')
            buildLog = open(logPath, 'w', 0)
            self.logs.append(buildLog)
            
            # TODO: Don't hard code dists. Most ports should only need base and 
            # maybe some sources to build. On AMD64 we probably also need the lib32 
            # dist. 
            dists = { 
                'base'  :   ['base'],
                'src'   :   ['sbase', 'scontrib', 'scrypto', 'sgnu', 'setc', 'sgames', 'sinclude', 'skrb5', 'slib', 'slibexec', 'srelease', 'sbin', 'ssecure', 'ssbin', 'sshare', 'ssys', 'subin', 'susbin', 'stools', 'srescue']
            }
            
            # Populate a new package chroot from the release binaries we built
            # or extracted from an ISO.
            pctx = BuildContext("Extracting release binaries to \"%s\"" % (release.pkgroot), logPath)
            assembler = builder.PackageChrootAssembler(release.releaseroot, release.pkgroot)
            eu = utils.ExecutionUnit(pctx, assembler.extract, dists, buildLog)
            self.oe.appendExecutionUnit(eu)

            # Mount devfs in the chroot
            pctx = BuildContext("Mount devfs in \"%s\"" % (release.pkgroot), logPath)
            devfs = builder.MountCommand('devfs', os.path.join(release.pkgroot, 'dev'), fstype='devfs')
            self.devmounts[devfs] = buildLog
            eu = utils.ExecutionUnit(pctx, devfs.mount, buildLog)
            self.oe.appendExecutionUnit(eu)
            
            # If we're using portsnap, run portsnap fetch now to get an updated 
            # snapshot.
            if (release.useportsnap):
                pc = builder.PortsnapCommand()
                pctx = BuildContext("Fetching up-to-date ports snapshot", logPath)
                eu = utils.ExecutionUnit(pctx, pc.fetch, buildLog)
                self.oe.appendExecutionUnit(eu)
                
                # Then portsnap extract a fresh ports tree in the chroot
                pctx = BuildContext("Extracting ports tree in \"%s\"" % (release.portsdir), logPath)
                eu = utils.ExecutionUnit(pctx, pc.extract, release.portsdir, buildLog)
                self.oe.appendExecutionUnit(eu)
                
            else:
                # Otherwise checkout the ports tree into the chroot with cvs
                cvs = builder.CVSCommand(release.cvsroot)
                pctx = BuildContext("%s release cvs checkout of \"%s\"" % (release.getSectionName(), release.portsdir), logPath)
                eu = utils.ExecutionUnit(pctx, cvs.checkout, 'HEAD', 'ports', release.portsdir, buildLog)
                self.oe.appendExecutionUnit(eu)

            # Mount distfiles cache directory in chroot if configured
            if self.distfilescache:
                mntpoint = os.path.join(release.pkgroot, 'usr', 'ports', 'distfiles')
                
                # The distfiles directory should always need to be created 
                # because we are working with a freshly created ports tree. 
                pctx = BuildContext("creating \"%s\" directory" % (mntpoint), logPath)
                eu = utils.ExecutionUnit(pctx, defer.execute, os.mkdir, mntpoint)
                self.oe.appendExecutionUnit(eu)
                
                pctx = BuildContext("Mount nullfs in \"%s\"" % (release.pkgroot), logPath)
                nullfs = builder.MountCommand(self.distfilescache, mntpoint, fstype='nullfs')
                self.distfilesmounts[nullfs] = buildLog
                eu = utils.ExecutionUnit(pctx, nullfs.mount, buildLog)
                self.oe.appendExecutionUnit(eu)
                
            # Make the packages directory. Like the distfiles directory above, 
            # this will always need to be created. Checking for its existence 
            # could lead to problems if that check is done before a deferred 
            # process deletes the pkgroot.
            pctx = BuildContext("creating \"%s\" directory" % (release.packagedir), logPath)
            eu = utils.ExecutionUnit(pctx, defer.execute, os.mkdir, release.packagedir)
            self.oe.appendExecutionUnit(eu)

            # Fire off a builder for each package
            for package in release.packages:
                pctx = BuildContext("Package build for release \"%s\"" % release.getSectionName(), logPath)

                # Grab the package build options
                buildoptions = {}
                if release.PackageBuildOptions:
                    buildoptions.update(release.PackageBuildOptions.Options)
                if package.BuildOptions:
                    buildoptions.update(package.BuildOptions.Options)

                # Add a package builder to the OrderedExecutor
                pb = builder.PackageBuilder(release.pkgroot, package.port, buildoptions)
                eu = utils.ExecutionUnit(pctx, pb.build, buildLog)
                self.oe.appendExecutionUnit(eu)

    def _cleanUpMounts(self):
        # Unmount all devfs mounts
        deferreds = []
        for mount, log in self.devmounts.iteritems():
            deferreds.append(mount.umount(log))
            
        # Same thing for distfiles nullfs mounts
        if self.distfilescache:
            for mount, log in self.distfilesmounts.iteritems():
                deferreds.append(mount.umount(log))

        d = defer.DeferredList(deferreds)
        return d

    def _decipherException(self, result, failure):
        # Decipher the BuildContext and raise a normal exception, with the message formatted for printing
        try:            
            bctx = failure.value.executionContext
            failure.value.originalFailure.raiseException()
        except builder.PackageBuildError, e:
            raise builder.PackageBuildError, "%s failed: %s.\nFor more information, refer to the package build log \"%s\"" % (bctx.description, e, bctx.logPath)
        except builder.CVSCommandError, e:
            raise builder.PackageBuildError, "%s failed: cvs returned: %s.\nFor more information, refer to the build log \"%s\"" % (bctx.description, e, bctx.logPath)
        except Exception, e:
            raise builder.PackageBuildError, "Unhandled package build error: %s" % (e)

    def _ebPackageBuild(self, failure):
        # Close our log files
        self._closeLogs()

        # Unmount anything in the chroot
        d = self._cleanUpMounts()

        # Decipher the exception
        d.addCallback(self._decipherException, failure)

        return d

    def _cbPackageBuild(self, result):
        # Close our log files
        self._closeLogs()

        # Unmount anything in the chroot
        return self._cleanUpMounts()

    def run(self):
        # Run!
        d = self.oe.run()
        d.addCallbacks(self._cbPackageBuild, self._ebPackageBuild)
        return d

class NetInstallAssemblerRunner(BuildRunner):
    """
    Run a set of installation builds
    """
    def __init__(self, config):
        super(NetInstallAssemblerRunner, self).__init__()
        self.oe = utils.OrderedExecutor()

        liveReleases = {}
        installAssemblers = []
        releaseAssemblers = []

        # Open the build log file
        logPath = os.path.join(config.Releases.buildroot, 'install.log')
        installLog = open(logPath, 'w', 0)
        self.logs.append(installLog)

        # Default BuildContext
        bctx = BuildContext("Installation build", logPath)

        # Clean the InstallRoot
        if (os.path.exists(config.Releases.installroot)):
            for directory in os.listdir(config.Releases.installroot):
                eu = utils.ExecutionUnit(bctx, threads.deferToThread, shutil.rmtree, os.path.join(config.Releases.installroot, directory))
                self.oe.appendExecutionUnit(eu)

        # Iterate through all installations
        for install in config.Installations.Installation:
            # Find the release for this installation
            for release in config.Releases.Release:
                if (release.getSectionName() == install.release.lower()):
                    # Found it. Add it to the dictionary of releases.
                    # It may already be in the dictionary from another installation.
                    liveReleases[release.getSectionName()] = release
                    break

            # Installation Name
            installName = install.getSectionName()

            # Default BuildContext
            bctx = BuildContext("%s installation build" % installName, logPath)

            # Generate the install.cfg
            installConfig = sysinstall.InstallationConfig(install, config)
            installConfigPath = os.path.join(config.Releases.buildroot, '%s-install.cfg' % (installName))
            outputFile = file(installConfigPath, 'w')

            # Serialize it
            eu = utils.ExecutionUnit(bctx, threads.deferToThread, installConfig.serialize, outputFile)
            self.oe.appendExecutionUnit(eu)

            # Close the output
            eu = utils.ExecutionUnit(bctx, defer.execute, outputFile.close)
            self.oe.appendExecutionUnit(eu)

            # Instantiate the installation assembler
            ia = builder.InstallAssembler(installName, install.description, release.releaseroot, installConfigPath)
            installAssemblers.append(ia)

        # Iterate over "live" releases
        for releaseName, release in liveReleases.iteritems():
                # Instantiate the release assembler
                if (len(release.localdata)):
                    ra = builder.ReleaseAssembler(releaseName, release.releaseroot, release.pkgroot, localData = release.localdata)
                else:
                    ra = builder.ReleaseAssembler(releaseName, release.releaseroot, release.pkgroot)

                releaseAssemblers.append(ra)

        # Reset default BuildContext
        bctx = BuildContext("Installation build", logPath)

        # Instantiate our NetInstall Assembler
        nia = builder.NetInstallAssembler(config.Releases.installroot, releaseAssemblers, installAssemblers)
        eu = utils.ExecutionUnit(bctx, nia.build, installLog)
        self.oe.appendExecutionUnit(eu)

    def _ebInstallBuild(self, failure):
        # Close our log files
        self._closeLogs()

        # Decipher the BuildContext and raise a normal exception, with the message formatted for printing
        try:            
            bctx = failure.value.executionContext
            failure.value.originalFailure.raiseException()
        except builder.NetInstallAssembleError, e:
            raise builder.NetInstallAssembleError, "%s failed: %s.\nFor more information, refer to the installation build log \"%s\"" % (bctx.description, e, bctx.logPath)
        except Exception, e:
            raise builder.NetInstallAssembleError, "Unhandled installation build error: %s" % (e)

    def _cbInstallBuild(self, result):
        # Close our log files
        self._closeLogs()

    def run(self):
        # Run!
        d = self.oe.run()
        d.addCallbacks(self._cbInstallBuild, self._ebInstallBuild)
        return d

