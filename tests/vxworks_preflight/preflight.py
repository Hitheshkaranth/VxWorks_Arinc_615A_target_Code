#!/usr/bin/env python3
"""Syntax-check the __VXWORKS__ branch of the production graph on the host.

The VxWorks-only code in lib/arinc_support/BuildConfig.hpp and
lib/arinc_support/BoostVxWorks.hpp is never compiled by the ordinary host
build, because no host compiler defines __VXWORKS__. This check compiles every
production translation unit with __VXWORKS__ and _WRS_KERNEL defined, against
the stub headers in sdk_stub/, so that branch is exercised by a compiler.

It proves the VxWorks branch is syntactically valid and that Boost selects the
VxWorks platform profile and the select reactor. It does NOT predict a
successful Workbench build: the stub headers are approximations backed by the
host libc, and linking, DKM load and on-target behaviour are untested.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

EXPECTED = {
    'BOOST_PLATFORM': 'VxWorks 7',
    'reactor': 'select',
    'local_sockets': 'disabled',
    'interrupter': 'socket',
}

CONFIG_PROBE = r'''
#include <boost/asio.hpp>
#include <cstdio>
#include <type_traits>
int main() {
  std::printf("BOOST_PLATFORM=%s\n", BOOST_PLATFORM);
#if defined(BOOST_ASIO_HAS_KQUEUE)
  std::printf("reactor=kqueue\n");
#elif defined(BOOST_ASIO_HAS_EPOLL)
  std::printf("reactor=epoll\n");
#elif defined(BOOST_ASIO_HAS_DEV_POLL)
  std::printf("reactor=dev_poll\n");
#else
  std::printf("reactor=select\n");
#endif
#if defined(BOOST_ASIO_HAS_LOCAL_SOCKETS)
  std::printf("local_sockets=enabled\n");
#else
  std::printf("local_sockets=disabled\n");
#endif
  // pipe() needs INCLUDE_POSIX_PIPES, which the office image omits.
  std::printf("interrupter=%s\n", std::is_same<boost::asio::detail::select_interrupter,
      boost::asio::detail::socket_select_interrupter>::value ? "socket" : "other");
  return 0;
}
'''

# The include chain the bundled Boost.Asio patch edits is extracted from the
# real header at run time, so reverting the patch is actually detected.
CHAIN_START = '#if (defined(__MACH__) && defined(__APPLE__))'


def extract_chain(socket_types):
    """Return the live poll/select #if chain as a probe with marker bodies."""
    lines = socket_types.read_text().splitlines()
    starts = [i for i, line in enumerate(lines)
              if line.replace(' ', '').startswith(CHAIN_START.replace(' ', ''))]
    if len(starts) != 1:
        raise SystemExit('Bundled Boost.Asio socket_types.hpp has an unexpected layout.')
    depth, body = 0, []
    for line in lines[starts[0]:]:
        # The VxWorks branch also carries the poll() shim's C code; only the
        # directives decide which header is selected, so skip everything else.
        # Line continuations of the opening #if are still kept.
        if not line.lstrip().startswith('#'):
            if body and body[-1].rstrip().endswith('\\'):
                body.append(line)
            continue
        stripped = line.lstrip('# \t')
        if stripped.startswith(('if', 'ifdef', 'ifndef')):
            depth += 1
        include = re.match(r'#\s*include\s*<([^>]+)>', line)
        if include:
            body.append('SELECTED=' + include.group(1).replace('/', '_').replace('.', '_'))
        else:
            body.append(line)
        if stripped.startswith('endif'):
            depth -= 1
            if depth == 0:
                return '\n'.join(body) + '\n'
    raise SystemExit('Could not delimit the Boost.Asio include chain.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--compiler', required=True)
    parser.add_argument('--sysroot', default='',
                        help='Host SDK sysroot, needed when the compiler is '
                             'invoked by absolute path (Apple toolchains).')
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    repo = here.parents[1]
    build = args.build.resolve()
    boost = Path((build / 'office-boost.txt').read_text().strip())
    sources = [Path(p) for p in (build / 'office-sources.txt').read_text().split('\n') if p]
    if not sources:
        raise SystemExit('Configure the offline root build before running the preflight.')

    flags = [
        '-std=c++17', '-fsyntax-only', '-Wall',
        '-D__VXWORKS__=1', '-D_WRS_KERNEL=1', '-DARINC_ENABLE_COMMAND_LINE=0',
        '-I', str(here / 'sdk_stub'),
        '-I', str(repo / 'lib'),
        '-I', str(repo / 'third_party/arinc_665/lib'),
        '-I', str(repo / 'app/arinc_615a_unit_test/arinc_615a_test_tha'),
        '-I', str(repo / 'workbench'),
        '-isystem', str(boost),
        '-I', str(build / 'include'),
        '-include', 'arinc_support/BuildConfig.hpp',
    ]
    # A compiler invoked by absolute path does not infer the Apple SDK, so the
    # host system headers the stubs pull in would be unreachable.
    if args.sysroot:
        flags += ['-isysroot', args.sysroot]

    failures = []
    from concurrent.futures import ThreadPoolExecutor

    def check(source):
        done = subprocess.run([args.compiler, *flags, str(source)],
                              capture_output=True, text=True)
        return source, done.returncode, done.stdout + done.stderr

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for source, code, output in pool.map(check, sources):
            if code != 0 or 'warning:' in output:
                failures.append((source, output))

    print(f'VxWorks-branch syntax check: {len(sources) - len(failures)}/{len(sources)} clean')
    for source, output in failures:
        print(f'--- {source}\n{output}')
    if failures:
        raise SystemExit('VxWorks preflight failed.')

    # The VxWorks platform profile and reactor must actually be the ones selected.
    probe = build / 'vxworks-preflight-config.cpp'
    probe.write_text(CONFIG_PROBE)
    binary = build / 'vxworks-preflight-config'
    done = subprocess.run([args.compiler, *[f for f in flags if f != '-fsyntax-only'],
                           str(probe), '-o', str(binary)], capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit('Could not build the VxWorks configuration probe:\n' + done.stderr)
    # BOOST_PLATFORM contains a space, so split on lines rather than whitespace.
    observed = dict(line.split('=', 1) for line in
                    subprocess.run([str(binary)], capture_output=True, text=True,
                                   check=True).stdout.splitlines() if '=' in line)
    for key, want in EXPECTED.items():
        if observed.get(key) != want:
            raise SystemExit(f'VxWorks preflight failed: {key} is '
                             f'{observed.get(key)!r}, expected {want!r}.')
    print('Boost platform profile: ' + observed['BOOST_PLATFORM'])
    print('Boost.Asio reactor:     ' + observed['reactor'])
    print('Asio local sockets:     ' + observed['local_sockets'])
    print('Asio interrupter:       ' + observed['interrupter'])

    # The bundled Asio patch must route a real cross-compiler to selectLib.h
    # while leaving every host platform on its existing header.
    chain = build / 'vxworks-preflight-chain.c'
    chain.write_text(extract_chain(boost / 'boost/asio/detail/socket_types.hpp'))
    cases = [
        ('VxWorks (__VXWORKS__)', ['-D__VXWORKS__=1'], 'SELECTED=selectLib_h'),
        ('VxWorks (__vxworks)', ['-D__vxworks=1'], 'SELECTED=selectLib_h'),
        ('Linux host', ['-D__linux__=1'], 'SELECTED=poll_h'),
        ('macOS host', ['-D__APPLE__=1', '-D__MACH__=1'], 'SELECTED=poll_h'),
        ('other POSIX', [], 'SELECTED=sys_poll_h'),
    ]
    for name, macros, want in cases:
        got = subprocess.run([args.compiler, '-E', '-P', '-undef', '-nostdinc',
                              *macros, str(chain)],
                             capture_output=True, text=True).stdout
        got = ''.join(got.split())
        if got != want:
            raise SystemExit(f'Asio include chain for {name}: got {got!r}, expected {want!r}.')
        print(f'Asio include chain, {name:<22} -> {want.split("=")[1]}')

    print('VxWorks preflight passed. This is a host syntax check, not a '
          'Workbench build; the licensed SDK remains the acceptance gate.')


if __name__ == '__main__':
    main()
