# ARINC 615A offline target

For the office handoff, extract `delivery/ARINC615A_OFFICE_READY.zip` and follow
its `START_HERE.md`. The same instructions are in [workbench/START_HERE.md](workbench/START_HERE.md).
Do not build all legacy folders recursively in Workbench.

The active root build is target-only by default. ARINC 665 binary support, TFTP,
local utility/checksum sources and Boost 1.88 headers are bundled in this repository.
No sibling repository, Git command, Internet download, Qt, external Helper,
ARINC 649, or separate ARINC 645 library is required for this target build.

Boost is still required (Asio networking, Hash2 hashing, property-tree JSON,
CRC, exceptions and header utilities); there is no separately installed Boost
runtime. See [dependency details](third_party/DEPENDENCIES.md).

**Validation status:** see [VALIDATION.md](VALIDATION.md). Host tests are not
proof of a VxWorks build. The exact licensed VxWorks 24.03 SDK/VSB/BSP and board
are required for final build, load and debug acceptance. The production graph is
C++17 and does not require `<format>`, `<span>`, `<concepts>`, or `<ranges>`.

## Offline host verification

With a C++17 compiler, CMake 3.24+, Ninja and Python 3 already installed:

```sh
cmake -S . -B build -G Ninja -DARINC_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
cmake --build build --target arinc_target_audit
python3 tools/prepare_office.py --build build \
  --source-commit "$(git rev-parse HEAD)" \
  --output delivery/ARINC615A_OFFICE_READY
```

The final packaging command requires a new destination (it refuses overwrites).
Boost is extracted locally with a verified SHA256, without downloading anything.
The generated handoff contains expanded headers and metadata: Python, CMake and
Git are not required for its native managed Workbench DKM build.
For an alternative static-library cross-build, see [VxWorksDKM.md](VxWorksDKM.md).

## Historical upstream documentation

The following describes the original desktop suite, **not the active target
build**. Its GUI/dependency-manager presets remain only as historical material;
do not use them for the offline target. Target instructions above take precedence.

This projects provides libraries and application implementing the ARINC 615A Data Loading Protocol.

The ARINC 615A is a standard used in the aviation industry for the transfer of software and data between avionics
systems.
It defines the format and structure of messages exchanged between the systems, as well as the procedures for initiating
and terminating transfers.
The protocol includes error detection and correction mechanisms to ensure data integrity.
The ARINC 615A Data Loading Protocol is used by avionics equipment for:
 - Reporting Equipment version information (Part Numbers, Versions, etc.),
 - Software/ Data Upload (SW Updates), and
 - Software/ Data Download.

## Key Features
 - Library for handling ARINC 615A data loader protocol Supplement 2, 3, and 4
 - Qt Libraries providing widgets for software loading operations
 - Applications implementing:
   - Data loading protocol via CLI,
   - Data loading protocol via GUI, and
   - Example Target Data Loader Application.

## Dependencies
First level dependencies:
- [Helper Library](https://git.thomas-vogt.de/thomas-vogt/helper)
- [Qt Icon Resources](https://git.thomas-vogt.de/thomas-vogt/qt_icon_resources)
- [ARINC 645 Tool Suite](https://git.thomas-vogt.de/thomas-vogt/arinc_645)
- [ARINC 665 Tool Suite](https://git.thomas-vogt.de/thomas-vogt/arinc_665)
- [TFTP Library](https://git.thomas-vogt.de/thomas-vogt/tftp)
- [Commands Library](https://git.thomas-vogt.de/thomas-vogt/commands)
- [Boost Libraries](https://www.boost.org/)
- libxml++
- [spdlog](https://github.com/gabime/spdlog)
- Optionally [Qt 6](https://www.qt.io/)

## Building
The library uses [CMake](https://cmake.org/) to handle build configuration.
CMake Presets are provided to generate builds compiling with:
- GNU GCC,
- Clang, and
- MSVC.

For each compiler and environment, the following variants can be built:
- Static debug,
- Static release,
- Shared debug, and
- Shared release.

Test Environments are:
- Linux,
- Windows MinGW, and
- Windows MSVC.

**Note:**
For managing dependencies, i.e. Windows MSVC, a VCPKG configuration is provided.

## License
This project is licensed under the terms of the [*Mozilla Public License Version 2.0* (MPL)](LICENSE).

## References
- ARINC 615A-4 - Software Data Loader Using Ethernet Interface
- ARINC 665-5 - Loadable Software Standards
- ARINC 645-1 - Common Terminology and Functions for Software Distribution and Loading

## Protocol Changes
This section only contains changes within the standards, which are respected within this library.

### ARINC 615A-1
- Protocol Filenames are all uppercase
- Explicit state UDP Port 59 for data loading
- Max Value for WAIT Message is 65535 (seconds)
- Host DL shall implement _TFTP block size option_ - THA may implement _TFTP block size option_
- Transfer size option shall not be used
- Definition of block number overflow
- timeout option shall not be used
- Limit text fields to 255/ 80 characters
- Set Protocol version to A2
- Add exception timer to status files
- Add reference to Sorcerer’s Apprentice Syndrome
### ARINC 615A-2
- Rename SNIP to FIND Protocol (FIND Identification of Network Devices)
- FIND is optional before transfer operation
- Set protocol version to A3
- Status description ignored for 0001 and 1002
- Change LCL file
  - Add multiple Target Hardware (Target Hardware Code and Serial Number)
  - For Part Numbers add Amendment
- Precisely describe exception timer
- Precisely describe estimated time
- Description length can be longer than actual text (null-terminated)
### ARINC 615A-3
- Set protocol version to A3
- TFTP Transfer size option is optional
- TFTP Timeout option is optional
- Add _Part Number Option_ (but copy-paste error and not usable)
- Add _Checksum Option_
- Add _Port Option_
- Add Status 0004 (in progress with status description)
### ARINC 615A-4
- _Part Number Option_ is described correctly
- _Checksum Option_ description is updated
