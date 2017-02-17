Unix EPControl package builder
---

Building Linux packages uses Docker with Dockerfiles located in this repository.

For 64 bits, these Dockerfiles inherit from public docker images.
For 32 bits, custom docker images were created using docker's contrib/mkimage, and some other open source scripts :

* [https://github.com/toopher/toopher-docker](https://github.com/toopher/toopher-docker) for CentOS 32 bit image building
* [https://github.com/daald/docker-brew-ubuntu-core-32bit](https://github.com/daald/docker-brew-ubuntu-core-32bit) for Ubuntu

These 32 bits image use 32 bits packages and a trick to ensure that "linux32" will be prepended to "docker run" commands.

Mac OS X packages are built directly on a Mac and do not use Docker.

The special `self` build builds the agent for the current host.


Requirements
---
First, modify settings.json

For building packages, [fpm](https://github.com/jordansissel/fpm/wiki) and unzip should be installed and on the $PATH.
Python3 should be installed on the building host and should provide the sh module (installable via pip).
Additionally, to build Linux packages, one should install :
* curl
* docker
* rpm for building rpm packages
* debhelper for building deb packages

On Mac OS X, Xcode should be installed, as well as wget and OpenSSL (typically using Homebrew; the path to Homebrew's OpenSSL install is appended to the CFLAGS and LDFLAGS used when building Python).

The special `self` build only requires python3.5 to be installed in its usual location /usr/lib/python3 (tested with Ubuntu 12.06 and Archlinux 2016.09.03).

Usage
---
```
usage: build.py [-h] [--instance-id INSTANCE_ID]
                {x86,x64}
                {ubuntu14.04,self,ubuntu12.04,sles12,centos6,macosx,debian7,debian8,sles11,centos7,ubuntu16.04}

Build a Unix EPControl agent package

positional arguments:
  {x86,x64}             The arch for which to build the package (unused when
                        building for current host)
  {ubuntu14.04,self,ubuntu12.04,sles12,centos6,macosx,debian7,debian8,sles11,centos7,ubuntu16.04}
                        The type of package to build

optional arguments:
  -h, --help            show this help message and exit
  --instance-id INSTANCE_ID
                        An optional instance id used to create a settings
                        package
```

License
---

See [COPYING](COPYING).