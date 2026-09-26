#!/usr/bin/env python3
"""Prepare a relocatable source-only Workbench handoff from a configured build.

Developer-side packaging only: office Workbench does not need Python or CMake.
Refuses to overwrite an existing destination.
"""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source-commit', required=True,
                        help='Git commit containing the packaged production sources')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    build = args.build.resolve()
    dest = args.output.resolve()
    if dest.exists():
        raise SystemExit('Destination exists; choose a new output directory.')
    boost = Path((build / 'office-boost.txt').read_text().strip())
    sources = [Path(p) for p in (build / 'office-sources.txt').read_text().splitlines()]
    if not sources or not (boost / 'boost/version.hpp').is_file():
        raise SystemExit('Configure the offline root build before packaging.')

    def source_path(path):
        relative = path.relative_to(repo)
        if relative.parts[:2] == ('third_party', 'arinc_665'):
            relative = Path(*relative.parts[2:])
        return Path('src') / relative

    def copy(path, target):
        output = dest / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, output)

    for source in sources:
        copy(source, source_path(source))
    header_roots = [repo / 'lib' / name for name in ('arinc_615a', 'tftp', 'arinc_support', 'arinc_checksum')]
    header_roots += [repo / 'third_party/arinc_665/lib/arinc_665',
                     repo / 'app/arinc_615a_unit_test/arinc_615a_test_tha', repo / 'workbench']
    for root in header_roots:
        for header in root.rglob('*'):
            if header.suffix not in ('.h', '.hpp', '.ipp') or 'test' in header.relative_to(root).parts:
                continue
            if 'host' in header.relative_to(root).parts or header.name == 'BoostAsioProgramOptions.hpp':
                continue
            copy(header, source_path(header))
    shutil.copytree(build / 'include', dest / 'include')
    shutil.copytree(boost / 'boost', dest / 'include/boost')
    for path in (repo / 'third_party_licenses').iterdir():
        if path.is_file():
            copy(path, Path('licenses') / path.name)
    copy(repo / 'LICENSE', Path('licenses/arinc_615a.LICENSE'))
    copy(repo / 'third_party/arinc_665/LICENSE', Path('licenses/arinc_665.LICENSE'))
    for name in ('START_HERE.md', 'VXWORKS_TEST_PROCEDURE.md', 'BUILD_OPTIONS.txt', 'target-config.json'):
        copy(repo / 'workbench' / name, Path(name))
    copy(repo / 'third_party/DEPENDENCIES.md', Path('DEPENDENCIES.md'))
    copy(repo / 'DEPENDENCY_REPORT.md', Path('DEPENDENCY_REPORT.md'))
    if (repo / 'VALIDATION.md').exists():
        copy(repo / 'VALIDATION.md', Path('VALIDATION.md'))
    copy(repo / 'tests/HostRunner.cpp', Path('tests/HostRunner.cpp'))
    copy(repo / 'tests/network_smoke.py', Path('tests/network_smoke.py'))
    copy(repo / 'tests/vxworks_target_test.py', Path('tests/vxworks_target_test.py'))
    copy(repo / 'tests/cli_acceptance.ps1', Path('tests/cli_acceptance.ps1'))
    copy(repo / 'tests/cli/arinc_615a_operation-exit-hang.patch',
         Path('tests/cli/arinc_615a_operation-exit-hang.patch'))
    (dest / 'BUILD_INFO.txt').write_text(
        'Source repository: https://github.com/UVDR-Team/ARINC-Target.git\n'
        f'Source commit: {args.source_commit}\n'
        'Package generator: tools/prepare_office.py\n'
        'Production sources: SOURCES.txt\n'
        'Integrity manifest: SHA256SUMS.txt\n')
    # HostRunner keeps its relative include; this header is never compiled.
    copy(repo / 'workbench/EntryPoints.h', Path('workbench/EntryPoints.h'))
    source_list = '\n'.join('  "' + source_path(p).as_posix() + '"' for p in sources)
    (dest / 'SOURCES.txt').write_text('\n'.join(source_path(p).as_posix() for p in sources) + '\n')
    (dest / 'CMakeLists.txt').write_text('''# Host verification of this exact handoff, not a VxWorks DKM linker recipe.
cmake_minimum_required(VERSION 3.24)
project(arinc_office_bundle LANGUAGES CXX)
if(CMAKE_SYSTEM_NAME STREQUAL "VxWorks")
  message(FATAL_ERROR "Use Workbench's managed DKM build for C++ initialization and BSP integration; see START_HERE.md")
endif()
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
find_package(Threads REQUIRED)
add_library(arinc_office_target STATIC
''' + source_list + '''
)
target_compile_features(arinc_office_target PUBLIC cxx_std_17)
target_include_directories(arinc_office_target PUBLIC src/lib src/workbench
  src/app/arinc_615a_unit_test/arinc_615a_test_tha)
target_include_directories(arinc_office_target SYSTEM PUBLIC include)
target_compile_options(arinc_office_target PUBLIC "SHELL:-include arinc_support/BuildConfig.hpp")
target_compile_definitions(arinc_office_target PUBLIC BOOST_ASIO_DISABLE_KQUEUE
  BOOST_ASIO_DISABLE_EPOLL BOOST_ASIO_DISABLE_DEV_POLL BOOST_ASIO_DISABLE_SERIAL_PORT
  BOOST_ASIO_DISABLE_LOCAL_SOCKETS)
target_link_libraries(arinc_office_target PUBLIC Threads::Threads)
add_executable(arinc_host_runner tests/HostRunner.cpp)
target_link_libraries(arinc_host_runner PRIVATE arinc_office_target)
enable_testing()
add_test(NAME self_test COMMAND arinc_host_runner --self-test)
find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(NAME network_transfers COMMAND "${Python3_EXECUTABLE}"
  "${CMAKE_SOURCE_DIR}/tests/network_smoke.py" --runner "$<TARGET_FILE:arinc_host_runner>")
set_tests_properties(network_transfers PROPERTIES TIMEOUT 120)
''')
    manifest = []
    for path in sorted(dest.rglob('*')):
        if path.is_file():
            manifest.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(dest).as_posix())
    (dest / 'SHA256SUMS.txt').write_text('\n'.join(manifest) + '\n')
    archive = dest.with_suffix('.zip')
    if archive.exists():
        raise SystemExit('Archive exists; refusing overwrite: ' + str(archive))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(dest.rglob('*')):
            if path.is_file():
                output.write(path, path.relative_to(dest.parent))
    print(f'Prepared {len(sources)} production translation units: {dest}')
    print(f'Archive: {archive} ({archive.stat().st_size} bytes)')
    print('SHA256: ' + hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
