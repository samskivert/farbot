# sysinstall.py vi:ts=4:sw=4:expandtab:
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

import os

class ConfigSection(object):
    """
    Abstract class implementing re-usable functions for install.cfg(8)
    configuration sections.
    """

    def _serializeOptions(self, output):
        """
        Serialize all install.cfg options for this section
        and the to an output file.

        Concrete subclasses MUST provide a sectionOptions list as a class
        attribute. This list must contain all valid install.cfg options for
        the section, in the order required by sysinstall(8).

        Given the sectionOptions list, this implementation will introspect
        'self' for attributes with names that match the sectionOptions.
        Any available attributes will be used, and any missing attributes
        will be ignored.

        @param output: Open, writable file handle
        """
        for option in self.sectionOptions:
            if hasattr(self, option):
                output.write('%s=%s\n' % (option, getattr(self, option)))

    def _serializeCommands(self, output):
        """
        Write out all commands listed in the sectionCommands class
        attribute.
        @param output: Open, writable file handle
        """
        for command in self.sectionCommands:
            output.write('%s\n' % (command))

class NetworkConfig(ConfigSection):
    """
    install.cfg(8) network configuration section.
    """
    # Section option names
    sectionOptions = (
        'hostname',     # New Server's Host Name
        'domainname',   # New Server's Domain Name
        'netdev',       # Network Interface
        'nfs',          # NFS Installation Media
        'tryDHCP'       # DHCP an address
    )
    # Default option values
    tryDHCP = 'YES'

    # Section commands
    sectionCommands = (
        'mediaSetNFS',
    )

    def __init__(self, section, config):
        """
        Initialize network configuration for a given
        installation.
        @param section: ZConfig Installation section
        @param config: ZConfig Farbot Config
        """
        # Install-specific Options
        self.hostname = section.hostname
        self.domainname = section.domain
        self.netdev = section.networkdevice

        # FarBot-wide Options
        self.nfshost = config.Releases.nfshost
        self.nfspath = os.path.join(config.Releases.installroot, section.release.lower())
        self.nfs = self.nfshost + ':' + self.nfspath

    def serialize(self, output):
        self._serializeOptions(output)
        self._serializeCommands(output)

class InstallationConfig(ConfigSection):
    """
    InstallationConfig instances represent a
    complete install.cfg file for sysinstall(8)
    """
    sectionOptions = (
        'debug',
        'nonInteractive',
        'noWarn'
    )
    # Defaults
    debug = 'YES'
    nonInteractive = 'YES'
    noWarn = 'YES'

    def __init__(self, section, config):
        """
        Initialize a new installation configuration.
        @param section: ZConfig Installation section
        @param config: ZConfig Farbot Config
        """
        self.name = section.getSectionName()

        # Network configuration
        self.networkConfig = NetworkConfig(section, config)

    def serialize(self, output):
        # Global configuration options
        self._serializeOptions(output)

        # Network configuration
        self.networkConfig.serialize(output)
