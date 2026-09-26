# Validation record

## Update: 25 September 2026 (Asia/Kolkata)

This supersedes the 23 September handoff. Host evidence only: the Wind River
compiler, SDK headers and the board were still unavailable, so the office
Workbench build and `VXWORKS_TEST_PROCEDURE.md` remain the acceptance gate.

### Office image audit

The exported office projects (UVDR_VIP/VSB_20260218, BSP
`nxp_layerscape_a72_2_0_7_4`, LLVM, CORTEX_A72) were checked against every
C/POSIX symbol the production graph needs, using the VSB library symbol
tables and the component definitions (CDF files). Gaps found and resolved in the code:

- `pipe()` needs `INCLUDE_POSIX_PIPES`, absent from the image; the DKM would
  not have loaded. Asio now wakes its select reactor through its loopback-socket
  interrupter (`ARINC_ASIO_SOCKET_SELECT_INTERRUPTER`, set by `BuildConfig.hpp`).
- No `pthread_rwlock_*` exists in the VSB; the three statistics classes use
  `std::mutex` instead of `std::shared_mutex`.
- No `poll()` or `socketpair()` in the image and no RAM disk (`/ram0`). The
  sample config and the board test use `/sd0a`.

### Repaired office Boost fixes

The 24 September hand edits to `socket_types.hpp` and `socket_ops.ipp` in the
unpacked handoff did not compile on any platform: a stray `#endif` split the
header's include chain; the poll shim used `nfds_t`, which the VxWorks headers
included here do not declare; and the socketpair shim called `closesocket()`,
passed the wrong arguments to `listen`, and hard-coded port 10000. They were also absent
from the repository, so any regeneration would have dropped them. Both headers
are now repaired in `third_party/boost_vxworks_overlay`, applied by
`cmake/BundledBoost.cmake`. The `mbuf.h` `m_data` macro is also removed in
`BuildConfig.hpp`. `SafeCast.ipp` gained a missing `<cstdint>` include.

### Executed checks (WSL Ubuntu, GCC 15.2, CMake 4.2)

- Clean repository build; 229/229 regression cases, 1,706 assertions.
- VxWorks preflight: 129/129 translation units clean. The select reactor,
  socket interrupter and `selectLib.h` chain are confirmed. The stub `sockLib.h` now defines
  `m_data`; removing the fix makes 8 units fail, so the check is effective.
- Dependency audit passed (CMake 4 absolute-path fix in `AuditTarget.cmake`).
- Regenerated handoff, unpacked fresh: clean build and tests, both normally and
  with the VxWorks interrupter forced on. No `pipe`, `eventfd`, `socketpair` or
  `pthread_rwlock` references remain.
- Board procedure rehearsed with the new on-target helpers and
  `tests/vxworks_target_test.py`, including from Windows Python to a WSL-hosted
  target: 9/9 checks (FIND, Information with retransmission, both downloads,
  upload, malformed/rejected inputs, soak), upload verified, clean stop.
- Interoperability with the real data loader, the ARINC-EXAMPLE CLI
  `arinc_615a_operation.exe` (MSVC, Windows), against the target application
  (VxWorks interrupter path) in WSL. `tests/cli_acceptance.ps1`: 7/7 checks.
  Covers FIND, Information (integrity valid), Operator and Media Defined
  Download (payload byte-identical) and Adhoc Upload of an ARINC 665 media set
  built by `arinc_665_media_set_compiler`; the target verified the upload.
  The CLI needed one fix, `tests/cli/arinc_615a_operation-exit-hang.patch`. Its
  command registry outlived the `io_context` (undefined behaviour), and the MSVC
  debug build hung at exit and lost its buffered results. The unpatched release
  build exited normally in 5 of 5 runs. Clean A/B test on the debug build (same
  build tree, a fresh target per run, completion confirmed on the wire each time):
  unpatched, 5 of 5 runs hung at exit with no result printed; patched, 0 of 5 hung
  and 5 of 5 printed `Operation completed`.
- One-command setup (`setup.sh`, `setup.bat`) verified from bare Docker images of
  Ubuntu 24.04, Ubuntu 22.04 (fetches CMake 3.31.6), Fedora 41, Debian 12, Arch
  and openSUSE Tumbleweed, all cloning from GitHub, on WSL Ubuntu and on
  Windows 11. The first matrix exposed two bugs, both fixed and re-verified:
  the audit on CMake 3.25, and GCC 16 building the target as C++20 (C++17 is now
  pinned).

## Original record

Date: 23 September 2026 (Asia/Kolkata)

## Result and scope

The target-only source graph builds successfully on the available macOS host
with AppleClang 17; all 128 production translation units compile in C++17 mode.
The independently implemented loopback peer
exercises real UDP/TFTP packets and all four ARINC 615A target operations. A
relocated copy of the office handoff also builds and passes with AddressSanitizer
and UndefinedBehaviorSanitizer enabled.

This is strong host-side evidence, but it is **not VxWorks 24.03 validation**.
The licensed Wind River compiler, exact VSB/BSP, LS1028ARDB target image and
board were not available. A Workbench compile, DKM link/load, on-board network
test, stop/restart and unload test remain mandatory. No document in this project
should be interpreted as a zero-error guarantee for an untested SDK/image.

## Executed checks

- Clean root Debug configuration using only the bundled ARINC 665 source and
  SHA-verified bundled Boost 1.88 headers; no network or sibling repository.
- Clean optimized Release compilation and executable link passed. A new-libc++
  stream symbol found by this check was removed in favor of portable `ostream::write`.
- All 229 original and added regression cases passed (1,613 assertions).
- C entry/self-test passed (FIND and initialization codecs plus SHA256 vector).
- Independent Python UDP/TFTP integration suite passed:
  FIND; Information and LCL; Upload with ARINC 665 header and a 4,097-byte file;
  Media Defined Download; Operator Defined Download listing/selection; clean stop.
- Lost first TFTP DATA acknowledgement recovered through retransmission.
- Malformed FIND input was ignored and the next valid request succeeded.
- Empty, malformed and path-traversal load headers were rejected; no file was
  written outside the configured upload directory and the server stayed alive.
- Corrupt and truncated uploads were rejected by stored size/CRC validation;
  a subsequent valid upload completed.
- Runtime start/stop/restart was tested for three cycles; a concurrent second
  runtime and unknown/disabled operations were rejected.
- Full test suite repeated ten consecutive times: all 30 CTest executions passed.
- Dependency audit passed across 128 production translation units, compiler
  include dependencies and undefined symbols of all four target archives.
- The relocated handoff compiled all 128 translation units as one target using
  the portable Boost.Asio `select` backend, then passed self/network tests under
  `-fsanitize=address,undefined -fno-sanitize-recover=all`.
- `git diff --check` passed; the final archive's SHA256 and per-file checksums
  are generated during final packaging.

## Important fixes validated by the negative tests

- Upload no longer continues after rejecting an empty ARINC 665 load header.
- Invalid/traversal load filenames are rejected before filesystem access.
- Stored upload length, CRC16 and optional ARINC 665 check value are verified.
- A pending status transmission is no longer replaced while active. The old
  behavior could trigger an assertion and corrupt the operation lifecycle when
  an upload was rejected quickly.
- Finalisation cancels its timer before invoking an owner callback that may
  release the operation object.
- A missing JSON configuration returns an error instead of silently starting
  with no enabled operations.

## Final office acceptance gate

Follow `START_HERE.md` inside the delivered ZIP. Record all of these before
calling the port complete: clean Workbench Debug build; no unresolved DKM
symbols; module load; self-test return 0; FIND; Information; known upload and
both downloads; corrupt/timeout/abort handling; stop/restart; clean unload;
stack and long-run memory checks. Preserve the exact VSB/VIP/BSP identifiers,
compiler output, target image identity and transfer logs with this record.
