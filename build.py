#!/usr/bin/env python3
"""
build.py : Build a Unix EPControl agent package

This file is part of EPControl.

Copyright (C) 2016  Jean-Baptiste Galet & Timothe Aeberhardt

EPControl is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

EPControl is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with EPControl.  If not, see <http://www.gnu.org/licenses/>.
"""
import shutil
import sys
import os
import errno
import re
import py_compile
from pathlib import Path
import argparse
import uuid
import tempfile
import json
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

import sh
from sh import wget, tar, unzip, fpm, patch, ErrorReturnCode


PYTHON_VERSION = "3.5.2"
AGENTLIB_VERSION = '0.0.0.1'
VERSION = '0.0.1'
DESCRIPTION_CORE = "EPControl agent core files"
DESCRIPTION = "Configuration package for EPControl agent"
MAINTAINER = "pokesec@chtimbo.org"
HOMEPAGE = "https://github.com/PokeSec"

AGENTLIB_URL = "https://github.com/PokeSec/agentlib/releases/download/{0}/agentlib_unix-{0}-py3-none-any.whl".\
    format(AGENTLIB_VERSION)

CWD = Path(os.path.dirname(os.path.realpath(__file__)))
BUILD_DIR = CWD / 'build'
DIST_DIR = CWD / 'dist'

DEST_TARGETS = {
    'centos6': 'rpm',
    'centos7': 'rpm',
    'debian7': 'deb',
    'debian8': 'deb',
    'sles11': 'rpm',
    'sles12': 'rpm',
    'ubuntu12.04': 'deb',
    'ubuntu14.04': 'deb',
    'ubuntu16.04': 'deb',
    'macosx': 'osxpkg',
    'self': None
}

TKTCL_RE = re.compile(r'^(_?tk|tcl).+\.(pyd|dll)', re.IGNORECASE)
DEBUG_RE = re.compile(r'_d\.(pyd|dll|exe)$', re.IGNORECASE)

EXCLUDE_FROM_LIBRARY = {
    '__pycache__',
    'ensurepip',
    'idlelib',
    'pydoc_data',
    'site-packages',
    'tkinter',
    'turtledemo',
    'venv',
    'pypiwin32_system32'
}
EXCLUDE_FILE_FROM_LIBRARY = {
    'bdist_wininst.py',
}


def is_not_debug(p):
    if DEBUG_RE.search(p.name):
        return False

    if TKTCL_RE.search(p.name):
        return False

    return p.name.lower() not in {
        '_ctypes_test.so',
        '_testbuffer.so',
        '_testcapi.so',
        '_testimportmultiple.so',
        '_testmultiphase.so',
        'xxlimited.so',
    }


def include_in_lib(p):
    name = p.name.lower()
    if p.is_dir():
        if name in EXCLUDE_FROM_LIBRARY:
            return False
        if name.startswith('plat-'):
            return False
        if name.endswith('.dist-info') or name.endswith('.egg-info'):
            return False
        if name == 'test' and p.parts[-2].lower() in ['pytool', 'lib']:
            return False
        if name in {'test', 'tests'} and p.parts[-3].lower() in ['pytool', 'lib']:
            return False
        return True

    if name in EXCLUDE_FILE_FROM_LIBRARY:
        return False

    suffix = p.suffix.lower()
    return suffix not in {'.pyc', '.pyo', '.exe'}

PKG_LAYOUT = [
    ('/', 'src:', 'settings.json', None),
    ('/', 'src:', 'trust.pem', None),
    ('/', 'epc:', 'EPControl', None),
    ('lib/', 'py:lib/', '**/*', include_in_lib),
]


def copy_to_layout(target, rel_sources):
    count = 0

    if target.suffix.lower() == '.zip':
        if target.exists():
            target.unlink()

        with ZipFile(str(target), 'w', ZIP_DEFLATED) as f:
            with tempfile.TemporaryDirectory() as tmpdir:
                for s, rel in rel_sources:
                    if rel.suffix.lower() == '.py':
                        pyc = Path(tmpdir) / rel.with_suffix('.pyc').name
                        try:
                            py_compile.compile(str(s), str(pyc), str(rel), doraise=True, optimize=2)
                        except py_compile.PyCompileError:
                            f.write(str(s), str(rel))
                        else:
                            f.write(str(pyc), str(rel.with_suffix('.pyc')))
                    else:
                        f.write(str(s), str(rel))
                    count += 1

    else:
        for s, rel in rel_sources:
            dest = target / rel
            try:
                dest.parent.mkdir(parents=True)
            except FileExistsError:
                pass

            if rel.suffix.lower() == '.py':
                pyc = Path(target) / rel.with_suffix('.pyc')
                try:
                    py_compile.compile(str(s), str(pyc), str(rel), doraise=True, optimize=2)
                except py_compile.PyCompileError:
                    shutil.copy(str(s), str(dest))
            else:
                shutil.copy(str(s), str(dest))
            count += 1

    return count


def rglob(root, pattern, condition):
    dirs = [root]
    recurse = pattern[:3] in {'**/', '**\\'}
    while dirs:
        d = dirs.pop(0)
        for f in d.glob(pattern[3:] if recurse else pattern):
            if recurse and f.is_dir() and (not condition or condition(f)):
                dirs.append(f)
            elif f.is_file() and (not condition or condition(f)):
                yield f, f.relative_to(root)


class LinuxPkgBuilder:
    def __init__(self, arch, dest, instance_id):
        from sh import docker
        self.docker = docker
        self.arch = arch
        self.dest = dest
        self.instance_id = instance_id
        self.docker_image = 'pokesec/python-{}-{}'.format(self.dest, self.arch)
        self.container_id = uuid.uuid4()

    def __enter__(self):
        self.docker.run('-dit',
                        '-v',
                        "{}:/opt/build".format(CWD),
                        '-w',
                        '/opt/build',
                        '--name',
                        self.container_id,
                        self.docker_image)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.container_id:
            self.docker.exec(self.container_id,
                             'rm',
                             '-rf',
                             '/opt/build/build')
            self.docker.stop(self.container_id)
            self.docker.rm(self.container_id)

    def build_epcontrol_main(self):
        print("Building EPControl")
        self.docker.exec(self.container_id,
                         'rm',
                         '-rf',
                         '/opt/build/build')
        self.docker.exec(self.container_id,
                         'mkdir',
                         '/opt/build/build')
        self.docker.exec(self.container_id,
                         'chmod',
                         '777',
                         '/opt/build/build')
        build_cmd = ['g++',
                     '-v',
                     '-Wsign-compare',
                     '-DNDEBUG',
                     '-g',
                     '-fwrapv',
                     '-O3',
                     '-Wall',
                     '-I/opt/python/Python-3.5.2/Include',
                     '-I/opt/python/Python-3.5.2',
                     'main.cpp',
                     '-L/opt/python/Python-3.5.2',
                     '-lpython3.5m',
                     '-lpthread',
                     '-ldl',
                     '-lutil',
                     '-lm',
                     '-lrt',
                     '-Xlinker',
                     '-export-dynamic',
                     '-o',
                     '/opt/build/build/EPControl']
        print(self.docker.exec(self.container_id, *build_cmd))

    def build_package(self):
        print("Building package")
        os.makedirs(str(BUILD_DIR), exist_ok=True)
        os.makedirs(str(BUILD_DIR / 'lib'), exist_ok=True)
        print(self.docker.exec(self.container_id,
                               'rm',
                               '-rf',
                               '/opt/python/python/lib/python3.5/test'
                               ))
        print(self.docker.exec(self.container_id,
                               'cp',
                               '-r',
                               '/opt/python/python/lib/python3.5/',
                               '/opt/build/build/lib/'))
        (BUILD_DIR / 'lib' / 'python3.5').rename(BUILD_DIR / 'lib' / 'pylib')
        print(self.docker.exec(self.container_id,
                               '/opt/python/python/bin/pip3',
                               'install',
                               AGENTLIB_URL,
                               '-t',
                               '/opt/build/build/lib/pytool'))

    def prepare_package(self):
        print("Preparing package")
        os.makedirs(str(BUILD_DIR / "prepared"), exist_ok=True)
        for t, s, p, c in PKG_LAYOUT:
            tmp = s.split(':')
            if tmp[0] == 'epc':
                s = BUILD_DIR
            elif tmp[0] == 'py':
                s = BUILD_DIR / 'lib'
            elif tmp[0] == 'src':
                s = CWD
            else:
                continue
            copied = copy_to_layout(BUILD_DIR / "prepared" / t.rstrip('/'), rglob(s, p, c))
            print('Copied {} files'.format(copied))

    def assemble_package(self):
        print("Assembling package")
        os.makedirs(str(DIST_DIR / self.arch / self.dest), exist_ok=True)
        print(fpm('-s', 'dir',
                  '-t', DEST_TARGETS[self.dest],
                  '-n', 'epcontrol-core',
                  '-f',
                  '--version', VERSION,
                  '-a', 'i386' if self.arch == 'x86' else 'amd64',
                  '-p', str(DIST_DIR / self.arch / self.dest),
                  '--license', 'GPLv3',
                  '--vendor', 'Pokesec',
                  '--maintainer', MAINTAINER,
                  '--url', HOMEPAGE,
                  '--description', DESCRIPTION_CORE,
                  '--before-install', 'linux/scripts/preinst.sh',
                  '--after-install', 'linux/scripts/postinst.sh',
                  '--before-upgrade', 'linux/scripts/preup.sh',
                  '{}/EPControl=/opt/epcontrol/'.format(str(BUILD_DIR/"prepared")),
                  '{}/lib=/opt/epcontrol/'.format(str(BUILD_DIR/"prepared")),
                  'settings.json=/opt/epcontrol/',
                  'trust.pem=/opt/epcontrol/',
                  'linux/systemd/epcontrol.service=/etc/systemd/system/epcontrol.service',
                  'linux/init.d/epcontrol=/etc/init.d/epcontrol',
                  'linux/upstart/epcontrol.conf=/etc/init/epcontrol.conf'))

    def assemble_conf_package(self):
        print("Assembling configuration package")
        os.makedirs(str(DIST_DIR / self.arch / self.dest), exist_ok=True)
        user_settings = {
            "INSTANCE_ID": self.instance_id
        }
        with tempfile.NamedTemporaryFile(mode='w') as f:
            json.dump(user_settings, f)
            f.flush()
            print(fpm('-s', 'dir',
                      '-t', DEST_TARGETS[self.dest],
                      '-n', 'epcontrol',
                      '-f',
                      '--version', VERSION,
                      '-a', 'i386' if self.arch == 'x86' else 'amd64',
                      '-d', 'epcontrol-core',
                      '-p', str(DIST_DIR / self.arch / self.dest),
                      '--license', 'GPLv3',
                      '--vendor', 'Pokesec',
                      '--maintainer', MAINTAINER,
                      '--url', HOMEPAGE,
                      '--description', DESCRIPTION,
                      '{}=/opt/epcontrol/user_settings.json'.format(f.name)))


class MacOSPkgBuilder:
    def __init__(self, instance_id):
        self.arch = 'x64'
        self.dest = 'macosx'
        self.instance_id = instance_id
        os.makedirs(str(BUILD_DIR), exist_ok=True)
        os.makedirs(str(BUILD_DIR / 'build'), exist_ok=True)
        os.makedirs(str(DIST_DIR), exist_ok=True)

    def __del__(self):
        pass
        # shutil.rmtree(str(BUILD_DIR/'build'))

    def build_python(self):
        os.chdir(str(BUILD_DIR))
        print("Building Python {}".format(PYTHON_VERSION))
        print(tar(
            wget('-O-', 'https://www.python.org/ftp/python/{0}/Python-{0}.tar.xz'.format(PYTHON_VERSION)),
            "xJ", _err_to_out=True))
        os.chdir(str(BUILD_DIR / "Python-{}".format(PYTHON_VERSION)))
        print(patch('-i', str(CWD / 'macosx' / 'osx-setup.patch'), 'setup.py'))
        print(sh.Command('./configure')(
            prefix=str(BUILD_DIR / 'python'),
            _err_to_out=True
        ))
        print(sh.Command('make')('-j4', _err_to_out=True))
        print(sh.Command('make')('install', _err_to_out=True))
        shutil.rmtree(str(BUILD_DIR / 'python' / 'lib' / 'python3.5' / 'test'))

    def build_epcontrol_main(self):
        os.chdir(str(CWD))
        print(sh.Command('clang++')(
            '-v',
            '-Wsign-compare',
            '-DNDEBUG',
            '-g',
            '-fwrapv',
            '-O3',
            '-Wall',
            '-I{}/Python-3.5.2/Include'.format(str(BUILD_DIR)),
            '-I{}/Python-3.5.2'.format(str(BUILD_DIR)),
            'main.cpp',
            '-L{}/Python-3.5.2'.format(str(BUILD_DIR)),
            '-lpython3.5m',
            '-lpthread',
            '-ldl',
            '-lutil',
            '-lm',
            '-o',
            str(BUILD_DIR / 'EPControl'),
            _err_to_out=True),
        )

    def build_package(self):
        os.chdir(str(CWD))
        os.makedirs(str(BUILD_DIR / 'build' / 'lib'), exist_ok=True)
        shutil.copy(str(BUILD_DIR / 'EPControl'), str(BUILD_DIR / 'build' / 'EPControl'))
        shutil.copytree(str(BUILD_DIR / 'python' / 'lib' / 'python3.5'), str(BUILD_DIR / 'build' / 'lib' / 'pylib'))
        print(sh.Command(str(BUILD_DIR / 'python' / 'bin' / 'pip3'))(
            'install',
            AGENTLIB_URL,
            '-t',
            str(BUILD_DIR / 'build' / 'lib' / 'pytool')))

    def assemble_package(self):
        print("Assembling package")
        os.makedirs(str(DIST_DIR / self.arch / self.dest), exist_ok=True)
        print(fpm('-s',
                  'dir',
                  '-t',
                  DEST_TARGETS[self.dest],
                  '-n',
                  'epcontrol-core',
                  '-f',
                  '--version',
                  VERSION,
                  '-a',
                  'amd64',
                  '-p',
                  str(DIST_DIR / self.arch / self.dest),
                  '--osxpkg-identifier-prefix',
                  'io.pokesec',
                  '--license',
                  'GPLv3',
                  '--vendor',
                  'Pokesec',
                  '--maintainer', MAINTAINER,
                  '--url', HOMEPAGE,
                  '--description', DESCRIPTION_CORE,
                  '--before-install',
                  'macosx/preinst.sh',
                  '--after-install',
                  'macosx/postinst.sh',
                  '{}/EPControl=/opt/epcontrol/'.format(str(BUILD_DIR / 'build')),
                  '{}/lib=/opt/epcontrol/'.format(str(BUILD_DIR / 'build')),
                  'settings.json=/opt/epcontrol/',
                  'trust.pem=/opt/epcontrol/',
                  'macosx/io.pokesec.epcontrol.plist=/Library/LaunchDaemons/io.pokesec.epcontrol.plist'))

    def assemble_conf_package(self):
        print("Assembling configuration package")
        os.makedirs(str(DIST_DIR / self.arch / self.dest), exist_ok=True)
        user_settings = {
            "INSTANCE_ID": self.instance_id
        }
        with tempfile.NamedTemporaryFile(mode='w') as f:
            json.dump(user_settings, f)
            f.flush()
            print(fpm('-s', 'dir',
                      '-t', DEST_TARGETS[self.dest],
                      '-n', 'epcontrol',
                      '-f',
                      '--version', VERSION,
                      '-a', 'amd64',
                      '-d', 'epcontrol-core',
                      '-p', str(DIST_DIR / self.arch / self.dest),
                      '--osxpkg-identifier-prefix', 'io.pokesec',
                      '--license', 'GPLv3',
                      '--vendor', 'Pokesec',
                      '--maintainer', MAINTAINER,
                      '--url', HOMEPAGE,
                      '--description', DESCRIPTION,
                      '{}=/opt/epcontrol/user_settings.json'.format(f.name)))


def build_on_host():
    print("Building EPControl on host")
    os.makedirs('dist/lib/pytool', exist_ok=True)
    print(sh.Command('pip3')((
        'install',
        AGENTLIB_URL,
        '-t',
        'dist/lib/pytool')))
    
    try:
        os.symlink('/usr/lib/python3.5', 'dist/lib/pylib')
    except OSError as e:
        if e.errno == errno.EEXIST:
            os.remove('dist/lib/pylib')
            os.symlink('/usr/lib/python3.5', 'dist/lib/pylib')
        else:
            raise e 
    
    build_args = ['-v',
                  '-Wsign-compare',
                  '-DNDEBUG',
                  '-g',
                  '-fwrapv',
                  '-O3',
                  '-Wall',
                  '-I/usr/include/python3.5m',
                  'main.cpp',
                  '-lpython3.5m',
                  '-lpthread',
                  '-ldl',
                  '-lutil',
                  '-lm',
                  '-lrt',
                  '-Xlinker',
                  '-export-dynamic',
                  '-o',
                  'dist/EPControl']
    for line in sh.Command('g++')(*build_args, _err_to_out=True, _iter=True):
        print(line)


def main():
    parser = argparse.ArgumentParser(description="Build a Unix EPControl agent package")
    parser.add_argument('arch', choices=['x86', 'x64'], help="The arch for which to build the package (unused when "
                                                             "building for current host)")
    parser.add_argument('dest',
                        choices=DEST_TARGETS.keys(),
                        help="The type of package to build")
    parser.add_argument('--instance-id', help="An optional instance id used to create a settings package")
    args = parser.parse_args()

    if args.dest == 'self':
        build_on_host()

    elif args.dest == 'macosx':
        if not sys.platform.startswith('darwin'):
            sys.exit("ERR: It is mandatory to use a Mac OS X operating system to build a pkg")
        if not args.arch == 'x64':
            sys.exit("ERR: Only 64 bits are supported for Mac OS X")
        pkg_builder = MacOSPkgBuilder(args.instance_id)
        if args.instance_id:
            pkg_builder.assemble_conf_package()
        else:
            pkg_builder.build_python()
            pkg_builder.build_epcontrol_main()
            pkg_builder.build_package()
            pkg_builder.assemble_package()

    else:
        with LinuxPkgBuilder(args.arch, args.dest, args.instance_id) as pkg_builder:
            if args.instance_id:
                pkg_builder.assemble_conf_package()
            else:
                try:
                    pkg_builder.build_epcontrol_main()
                    pkg_builder.build_package()
                    pkg_builder.prepare_package()
                    pkg_builder.assemble_package()
                except ErrorReturnCode as e:
                    print("Build failed")
                    print(e)
                    sys.exit(1)

if __name__ == '__main__':
    main()
