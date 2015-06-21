## Introduction

Farbot automates building of netinstall/PXE boot FreeBSD releases. It features a simple
configuration file based on the concept of "Installations", "!PackageSets", and "!PartitionMaps."

Farbot currently handles the following:

  * Building FreeBSD releases, including grabbing any source needed. It is also possible to just
    extract a release from a FreeBSD CD ISO if a custom build is unnecessary.
  * Building packages for each release, derived from per installation package sets.
  * Laying out an NFS/TFTP exportable file system structure for all built releases, customized
    for each installation type.
  * Generation of a customized bootloader with options to install each installation type.

## Requirements
  * [Python](http://www.python.org) 2.4 or greater
  * [Zconfig](http://www.zope.org/Members/fdrake/zconfig/)
  * To actually perform a release build farbot must be running on a
    [FreeBSD](http://www.freebsd.org) host.


## Installation
Farbot uses the standard Python distutils. To install, run setup.py:

```
./setup.py install
```

Farbot includes a suite of tests which can be run before installing if desired:

```
./runtests.py
```

Farbot will be installed in the Python site-packages directory. The farbot command line tool will
be installed in the Python-specified bin directory. An example configuration file, farbot.conf, is
supplied with the source distribution.

Farbot is also available in the FreeBSD ports collection as sysutils/farbot.
