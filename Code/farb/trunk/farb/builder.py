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

from twisted.internet import reactor, defer, protocol
import os, re

import farb

# make(1) path
MAKE_PATH = '/usr/bin/make'

# cvs(1) path
CVS_PATH = '/usr/bin/cvs'

# Standard FreeBSD src location
FREEBSD_REL_PATH = '/usr/src/release'

# Relative path of newvers.sh file in the FreeBSD CVS repository
NEWVERS_PATH = 'src/sys/conf/newvers.sh'

# Exceptions
class CVSCommandError(farb.FarbError):
    pass

class NCVSParseError(CVSCommandError):
    pass

class MDConfigCommandError(farb.FarbError):
    pass

class MakeCommandError(farb.FarbError):
    pass

class ReleaseBuildError(farb.FarbError):
    pass

class MakeProcessProtocol(protocol.ProcessProtocol):
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
            self.d.errback(MakeCommandError(status.value.exitCode))


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


class MakeCommand(object):
    """
    make(1) command context
    """
    def __init__(self, directory, target, options):
        """
        Create a new MakeCommand instance
        @param directory: Directory in which to run make(1)
        @param target: Makefile target
        @param options: Dictionary of Makefile options
        """
        self.directory = directory
        self.target = target
        self.options = options

    def make(self, log):
        """
        Run make(1)
        @param log: Open log file
        """

        # Create command argv
        argv = [MAKE_PATH, '-C', self.directory, self.target]
        for option, value in self.options.items():
            argv.append("%s=%s" % (option, value))

        d = defer.Deferred()
        protocol = MakeProcessProtocol(d, log)
        reactor.spawnProcess(protocol, MAKE_PATH, argv)

        return d


class ReleaseBuilder(object):
    makeTarget = 'release'
    defaultMakeOptions = {
        'NOPORTS' : 'no',
        'NODOC' : 'no'
    }

    """
    Build a FreeBSD Release
    """
    def __init__(self, cvsroot, cvstag, buildroot, makecds=False):
        """
        Create a new ReleaseBuilder instance.

        @param cvsroot: Path to FreeBSD CVS Repository
        @param cvstag: FreeBSD Release Tag
        @param buildroot: Working build directory
        @param makecds: Boolean enables the creation of ISO CD installation images.
        """
        self.cvsroot = cvsroot
        self.cvstag = cvstag
        self.buildroot = buildroot
        self.makecds = makecds
        self.chroot = os.path.join(self.buildroot, 'chroot')

    def _ebBuildError(self, failure):
        try:
            failure.raiseException()
        except CVSCommandError, e:
            raise ReleaseBuildError, "An error occured extracting the release name from \"%s\": %s" % (self.cvsroot, e)
        except MakeCommandError, e:
            raise ReleaseBuildError, "An error occured building the release in \"%s\", make command returned: %s" % (self.buildroot, e)

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
        reactor.spawnProcess(pp, CVS_PATH, [CVS_PATH, '-R', '-d', self.cvsroot, 'co', '-p', '-r', self.cvstag, NEWVERS_PATH])
        return d
