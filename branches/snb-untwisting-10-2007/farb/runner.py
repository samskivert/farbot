# runner.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2007-2008 Three Rings Design, Inc.
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
from farb import builder, sysinstall

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
    
    def _copyFromISO(self, release):
        # Create the ISOs mount point if needed
        mountpoint = os.path.join(release.buildroot, 'mnt')
        if (not os.path.exists(mountpoint)):
            self.log.write("Creating mount point \"%s\" for ISO\n" % mountpoint)
            os.mkdir(mountpoint)

        # Mount the ISO
        self.log.write("Mount ISO at \"%s\"\n" % mountpoint)
        mdconfig = builder.MDConfigCommand(release.iso)                
        self.isomount = builder.MDMountCommand(mdconfig, mountpoint, fstype='cd9660')
        self.isomount.mount(self.log)
    
        # Copy ISO contents to release directory
        self.log.write("Release %s copying to %s\n" % (release.getSectionName(), release.releaseroot))
        isoReader = builder.ISOReader(mountpoint, release.releaseroot)
        isoReader.copy(self.log)
    
    def run(self):
        # Iterate through all releases, starting a release build for all
        # releases referenced by an Installation.
        for release in self.config.Releases.Release:
            releaseName = release.getSectionName()
            
            # Check all installations for a reference to this release
            for install in self.config.Installations.Installation:
                releaseFound = False
                if (releaseName == install.release.lower()):
                    releaseFound = True
                    break
            if (not releaseFound):
                # Skip the release, it's not used by any installation
                continue

            logPath = os.path.join(release.buildroot, 'build.log')
            try:
                try:
                    # Create the build directory
                    if (not os.path.exists(release.buildroot)):
                        os.makedirs(release.buildroot)
            
                    # Open the build log file
                    self.log = open(logPath, 'w', 0)
            
                    if (release.binaryrelease):
                        self._copyFromISO(release)
                    else:
                        # Instantiate our builder
                        self.log.write("Starting build of release %s\n" % releaseName)
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
                    self.log.write("Unmounting ISO at \"%s\"\n" % self.isomount.mountpoint)
                    self.isomount.umount(self.log)
                
                # Close our log file
                self._closeLog()

class PackageBuildRunner(BuildRunner):
    """
    Run a set of package builds
    """
    def __init__(self, config):
        super(PackageBuildRunner, self).__init__(config)
    
    def run(self):
        devmount = None
        distfilesmount = None
        
        if self.config.PackageSets:
            distfilescache = self.config.PackageSets.distfilescache
        
        try:
            # Create the distfiles cache directory if necessary
            if (distfilescache and not os.path.exists(distfilescache)):
                os.makedirs(distfilescache)
        except Exception, e:
            raise builder.PackageBuildRunnerError, "Failed to create distfiles cache directory %s: %s" % (distfilescache, e)

        # Iterate through all releases, starting a package build for all
        # listed packages
        for release in self.config.Releases.Release:
            releaseName = release.getSectionName()
            # Grab the list of packages set by verifyPackages()
            if (not release.packages):
                continue
            
            logPath = os.path.join(release.buildroot, 'packaging.log')
            try:
                try:
                    # Open a packaging log file
                    self.log = open(logPath, 'w', 0)
            
                    # Get list of distribution sets to use. If src or kernels 
                    # are the defined dist, we'll need to get a sub-list of 
                    # distribution sets from SourceDists and/or KernelDists
                    dists = {}
                    for dist in release.dists:
                        if dist == 'src':
                            dists[dist] = release.sourcedists
                        elif dist == 'kernels':
                            dists[dist] = release.kerneldists
                        else:
                            dists[dist] = [dist]
            
                    # Populate a new package chroot from the release binaries we 
                    # built or extracted from an ISO.
                    self.log.write("Extracting release binaries to \"%s\"\n" % release.pkgroot)
                    assembler = builder.PackageChrootAssembler(release.releaseroot, release.pkgroot)
                    assembler.extract(dists, self.log)

                    # Mount devfs in the chroot
                    self.log.write("Mount devfs in \"%s\"\n" % release.pkgroot)
                    devmount = builder.MountCommand('devfs', os.path.join(release.pkgroot, 'dev'), fstype='devfs')
                    devmount.mount(self.log)
                    
                    # If we're using portsnap, run portsnap fetch now to get an 
                    # updated snapshot.
                    if (release.useportsnap):
                        self.log.write("Fetching up-to-date ports snapshot\n")
                        pc = builder.PortsnapCommand()
                        pc.fetch(self.log)
                
                        # Then portsnap extract a fresh ports tree in the chroot
                        self.log.write("Extracting ports tree in \"%s\"\n" % release.portsdir)
                        pc.extract(release.portsdir, self.log)
                    
                    else:
                        # Otherwise checkout the ports tree into the chroot with cvs
                        self.log.write("%s release cvs checkout of \"%s\"\n" % (releaseName, release.portsdir))
                        cvs = builder.CVSCommand(release.cvsroot)
                        cvs.checkout('HEAD', 'ports', release.portsdir, self.log)
                    
                    # Mount distfiles cache directory in chroot if configured
                    if distfilescache:
                        mntpoint = os.path.join(release.pkgroot, 'usr', 'ports', 'distfiles')
                        
                        # The distfiles directory should always need to be 
                        # created because we are working with a freshly created 
                        # ports tree. 
                        self.log.write("Creating \"%s\" directory\n" % mntpoint)
                        os.mkdir(mntpoint)
                        
                        self.log.write("Mount nullfs in \"%s\"\n" % release.pkgroot)
                        nullfs = builder.MountCommand(distfilescache, mntpoint, fstype='nullfs')
                        distfilesmount = nullfs
                        nullfs.mount(self.log)
                    
                    # Make the packages directory. 
                    self.log.write("Creating \"%s\" directory\n" % release.packagedir)
                    os.mkdir(release.packagedir)
                    
                    # Fire off a builder for each package
                    for package in release.packages:
                        self.log.write("Starting build of package \"%s\" for release \"%s\"\n" % (package.port, releaseName))

                        # Grab the package build options
                        buildoptions = {}
                        if release.PackageBuildOptions:
                            buildoptions.update(release.PackageBuildOptions.Options)
                        if package.BuildOptions:
                            buildoptions.update(package.BuildOptions.Options)

                        # Build it
                        pb = builder.PackageBuilder(release.pkgroot, package.port, buildoptions)
                        pb.build(self.log)
        
                # Catch any exception. If it's from a command or package builder
                # the relevant details should be contained in the exception 
                # text.
                except Exception, e:
                    raise PackageBuildRunnerError, "Package build for release %s failed: %s\nFor more information, refer to the package build log \"%s\"" % (releaseName, e, logPath)
        
            finally:
                # Unmount any devfs and distfiles nullfs mounts
                if devmount:
                    self.log.write("Unmounting devfs at %s\n" % devmount.mountpoint)
                    devmount.umount(self.log)
                    devmount = None
                if distfilesmount:
                    self.log.write("Unmounting distfiles cache at %s\n" % distfilesmount.mountpoint)
                    distfilesmount.umount(self.log)
                    distfilesmount = None
            
                # Close our log file
                self._closeLog()

class NetInstallAssemblerRunner(BuildRunner):
    """
    Run a set of installation builds
    """
    def __init__(self, config):
        super(NetInstallAssemblerRunner, self).__init__(config)

    def run(self):
        liveReleases = {}
        installAssemblers = []
        releaseAssemblers = []

        logPath = os.path.join(self.config.Releases.buildroot, 'install.log')        
        try:
            try:
                # Open the build log file
                self.log = open(logPath, 'w', 0)

                # Clean the InstallRoot
                if (os.path.exists(self.config.Releases.installroot)):
                    for directory in os.listdir(self.config.Releases.installroot):
                        shutil.rmtree(os.path.join(self.config.Releases.installroot, directory))

                # Iterate through all installations
                for install in self.config.Installations.Installation:
                    # Find the release for this installation
                    for release in self.config.Releases.Release:
                        if (release.getSectionName() == install.release.lower()):
                            # Found it. Add it to the dictionary of releases.
                            # It may already be in the dictionary from another installation.
                            liveReleases[release.getSectionName()] = release
                            break

                    # Installation Name
                    installName = install.getSectionName()

                    # Generate the install.cfg
                    installConfig = sysinstall.InstallationConfig(install, self.config)
                    installConfigPath = os.path.join(self.config.Releases.buildroot, '%s-install.cfg' % (installName))
                    self.log.write("Generating install configuration file %s\n" % installConfigPath)
                    outputFile = file(installConfigPath, 'w')
                    installConfig.serialize(outputFile)
                    outputFile.close()

                    # Instantiate the installation assembler
                    self.log.write("Beginning %s installation build\n" % installName)
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

                # Instantiate our NetInstall Assembler
                nia = builder.NetInstallAssembler(self.config.Releases.installroot, releaseAssemblers, installAssemblers)
                nia.build(self.log)
            
            except builder.NetInstallAssembleError, e:
                raise NetInstallAssemblerRunnerError, "Failure setting up installation data: %s.\nFor more information, refer to the installation assembler log \"%s\"" % (e, logPath)
            except Exception, e:
                raise NetInstallAssemblerRunnerError, "Unhandled installation build error: %s" % (e)

        finally:
            # Close our log file
            self._closeLog()
