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

# make(1) path
MAKE_PATH = '/usr/bin/make'

# Standard FreeBSD src location
FREEBSD_REL_PATH = '/usr/src/release'

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
        self.d.callback(status.value.exitCode)

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
    """
    Build a FreeBSD Release
    """
    def __init__(self, cvsroot, cvstag, buildroot):
        """
        Create a new ReleaseBuilder instance.

        @param cvsroot: Path to FreeBSD CVS Repository
        @param cvstag: FreeBSD Release Tag
        @param buildroot: Working build directory
        """
        self.cvsroot = cvsroot
        self.cvstag = cvstag
        self.buildroot = buildroot

    def build(self, log):
        """
        Build the release
        @param log: Open log file
        @return Returns a deferred that will be called when make(1) completes
        """
        makecmd = MakeCommand(FREEBSD_REL_PATH, 'release', {})
        return makecmd.make(log)
