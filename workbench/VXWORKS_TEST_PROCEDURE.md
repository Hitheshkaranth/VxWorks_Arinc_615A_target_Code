# ARINC 615A target: VxWorks 24.03 acceptance test procedure

Platform: VxWorks 24.03, Wind River Workbench 4, Windows PC as the test host.

## 1. Purpose and scope

This procedure shows that the ARINC 615A target module builds, loads and runs on
the office VxWorks 24.03 image, and that a Windows PC can reach it over real
Ethernet with every supported operation: FIND, Information, Upload, Media Defined
Download and Operator Defined Download. It also covers the negative cases and the
module lifecycle.

It does **not** certify anything. The limits in `START_HERE.md` still apply. This is a
protocol and file-transfer check, not firmware activation, flash programming,
secure boot or a certified software-update procedure. A result is valid only for
the exact VSB, BSP, image and toolchain written in the results record (§6).

## 2. Test setup

```
 +------------------------------------+          +-------------------------------+
 | Windows PC                         |          | VxWorks 24.03 board           |
 |  - Workbench 4 (build, load, debug)|  Ethernet|  - ARINC DKM (.out) loaded    |
 |  - Python 3.8+ (test driver)       |<-------->|  - task tArinc: arinc615aRun  |
 |  - tests\vxworks_target_test.py    | same IPv4|  - /sd0a/arinc_test (fixtures)|
 |  IP e.g. 192.168.0.2               |  subnet  |  IP e.g. 192.168.0.3          |
 +------------------------------------+          +-------------------------------+
            |  serial console (COMx, 115200 8N1) or Workbench Host Shell
            +------------------------------------------> kernel shell (C interpreter)
```

UDP traffic: PC to board on port 1001 (FIND) and port 59 (TFTP). The board then
opens TFTP transfers back to ephemeral UDP ports on the PC.

## 3. Prerequisites

### 3.1 Target image (VSB/VIP), set up by the platform engineer

The image must provide:

- C++ runtime with exceptions and RTTI, and C++17 `std::filesystem`
- POSIX pthreads and `clock_gettime` (the code uses no POSIX semaphores)
- `select`, IPv4 UDP sockets, and a configured network interface
- a writable filesystem for the test root
- the kernel shell, plus `checkStack`, `memShow`, and the loader and unloader (`ld`, `unld`)

**Office image check (UVDR_VIP/VSB_20260218, BSP `nxp_layerscape_a72_2_0_7_4`, LLVM,
CORTEX_A72).** The exported project files were checked on 25 Sep 2026 against every
item above. All are present; the one gap found (no POSIX pipes) is handled in the code:

| Need | Found in the office image |
| --- | --- |
| C++ runtime, exceptions, RTTI | `INCLUDE_CPLUS`, `INCLUDE_CPLUS_LANG`, `INCLUDE_CPLUS_STDLIB`; VSB `LIBCPLUS_STD` with C++2017. `__cxa_throw`, `__dynamic_cast` and `std::exception` typeinfo are in `libllvmcplus` |
| `std::filesystem` | The Dinkumware library in `libcplusplus` has every primitive used: `_Make_dir`, `_Remove_dir`, `_Open_dir`/`_Read_dir`, `_Stat`, `_Unlink`, `_Rename`, `_File_size` |
| `std::mutex` / threads | `_Mtx_*`, `_Cnd_*`, `_Thrd_*` are in `libc` |
| POSIX | `INCLUDE_POSIX_PTHREADS`, `INCLUDE_POSIX_PTHREAD_SCHEDULER`, `INCLUDE_POSIX_CLOCKS`, `INCLUDE_POSIX_TIMERS` |
| Network | `INCLUDE_IPNET`, `INCLUDE_IPCOM_USE_INET`, `INCLUDE_SOCKLIB`, `INCLUDE_SELECT` |
| Asio reactor wake-up | `INCLUDE_POSIX_PIPES` is **absent**, so `pipe()` would be unresolved at load. `BuildConfig.hpp` sets `ARINC_ASIO_SOCKET_SELECT_INTERRUPTER`, so Asio uses a loopback TCP pair instead (`accept`, `listen`, `connect`, all in IPNET). The preflight checks this |
| Storage | `INCLUDE_DOSFS` and the SD bus. **No RAM-disk driver**, so `/ram0` does not exist |
| Shell and tools | `INCLUDE_SHELL_INTERP_C`, `INCLUDE_LOADER`, `INCLUDE_UNLOADER`, `INCLUDE_STANDALONE_SYM_TBL`, `INCLUDE_MEM_SHOW`, `INCLUDE_TASK_SHOW`, `INCLUDE_DEBUG_AGENT` with host FS |

This check was made against the project files only, so it proves presence, not a
successful link. Phase A/B is still the proof.

**Test root on this board.** The UVDR application uses the SD partitions `/sd0a`,
`/sd0b`, `/sd0d`, `/sd1a` and `/mmc1`. Use a dedicated folder that nothing else uses,
for example `/sd0a/arinc_test`. `arinc615aPrepareTest` empties `<root>/upload`, so never
point it at a folder that holds recordings or configuration. Check that the card is
mounted and writable first:

```c
-> devs
-> ls "/sd0a"
```

The commands below use `/sd0a/arinc_test`. On another image with a RAM disk, any
writable root such as `/ram0/arinc` works the same way.

Network settings of the office image. It does **not** include the `ifconfig`
shell command, telnet or `ping`, so the IP comes from the boot line:

| | Value in `UVDR_VIP_20260218` |
| --- | --- |
| Boot line | `memac(0,0)host:vxWorks h=192.168.0.2 e=192.168.0.3` |
| Board IP / interface | `192.168.0.3` on `memac0` (boot-line `e=`) |
| PC (host) IP | `192.168.0.2` (boot-line `h=`) |
| Console | `/ttyS0`, 115200 8N1 |

To use another address, change `e=` in the boot parameters and reboot. Confirm
the address from the PC with `ping 192.168.0.3`.

### 3.2 Windows PC

- Workbench 4 with the office's VxWorks 24.03 SDK, and the same VSB/BSP as the image.
- Python 3.8 or later on PATH. Check with `python --version`. Only the standard library is needed.
- A Windows Firewall rule that lets Python receive UDP. Run this in an elevated `cmd`:

```bat
netsh advfirewall firewall add rule name="ARINC615A test (python UDP in)" ^
  dir=in action=allow protocol=UDP profile=private program="C:\Path\To\python.exe"
```

Use `where python` to find the real path. The Ethernet adapter that faces the board
must be in the **Private** network profile. Check with the PowerShell cmdlet
`Get-NetConnectionProfile`. Remove the rule after testing:

```bat
netsh advfirewall firewall delete rule name="ARINC615A test (python UDP in)"
```

## 4. Procedure

Type kernel shell commands at the `->` prompt. Windows commands run in `cmd` from
the extracted package folder, for example `C:\ARINC\ARINC615A_OFFICE_READY`.

### Phase A: Build the DKM in Workbench

1. Create and configure the VxWorks Downloadable Kernel Module project as described in
   `START_HERE.md` §1–2. Use the same VSB, BSP, CPU and ABI as the running image,
   C++17, and the build options from `BUILD_OPTIONS.txt`.
2. Build input is `src/` only. `SOURCES.txt` now also lists
   **`src/workbench/TestSupport.cpp`**, which provides the test entry points used below.
   Make sure the file is included in the build.
3. Build the Debug configuration. **Expected:** 0 errors, and the output `.out` is produced.
   Save the full build console log.

### Phase B: Connect and load

1. In Workbench, open **Terminals / Target Connections**. Create a new VxWorks 7 connection
   to the board's IP and connect. The target server must come up.
2. Load the module. Use either method:
   - Workbench: right-click the `.out` and choose **Download** (or Load) to the connection.
   - Kernel shell, loading through the target server file system (TSFS). The path is
     relative to the target server's root directory set in the connection properties,
     so adjust it to your connection:

```c
-> ld < /tgtsvr/<path-below-tgtsvr-root>/ARINC615A.out
```

3. Check that the load reported **no unresolved symbols**. The loader prints any it finds.
   Then confirm the entry points exist:

```c
-> lkup "arinc615a"
```

**Expected:** the output lists `arinc615aSelfTest`, `arinc615aDemo`, `arinc615aRun`,
`arinc615aStop`, `arinc615aPrepareTest`, `arinc615aVerifyTestUpload`, and
`arinc615aWriteFixtures`.

### Phase C: Self-test

```c
-> arinc615aSelfTest
```

**Expected:** the console prints `ARINC self-test PASS ...` and the return value is `value = 0 = 0x0`.

### Phase D: Prepare fixtures and start the loader

```c
-> arinc615aPrepareTest "/sd0a/arinc_test"
-> ls "/sd0a/arinc_test/download"
-> taskSpawn("tArinc", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
-> i
```

- `arinc615aPrepareTest` returns 0. It creates `upload/` (emptied), `download/`
  (`demo.LUH`, `payload.bin`, `empty.LUH`, `traversal.LUH`) and `test-config.json`.
  The config uses FIND port 1001, TFTP port 59, target `ARINC_1`, thwId `ARINC`,
  serial `TEST001` and a 1 s TFTP timeout.
- `taskSpawn` arguments: priority 100, `0x01000000` = `VX_FP_TASK`, and a 1 MiB stack.
- **Expected:** `i` shows the task `tArinc` in state `PEND` (waiting on network I/O),
  not `SUSPEND`, and it has not exited.

### Phase E: Run the Windows test driver

```bat
ping 192.168.0.3
python tests\vxworks_target_test.py --target 192.168.0.3
```

Full options, with their default values:

```bat
python tests\vxworks_target_test.py --target <board-ip> [--find-port 1001] [--tftp-port 59]
       [--target-id ARINC_1] [--thw-id ARINC] [--serial TEST001] [--timeout 5]
       [--soak N] [--bind 0.0.0.0]
```

Use `--bind <PC-IP>` if the PC has several adapters and transfers time out after FIND works.

The script runs these steps and prints one `PASS:` line for each:

| Step | What it checks |
| --- | --- |
| FIND | The board answers a FIND request over UDP with thwId `ARINC`. |
| Information | LCI accepted. One DATA packet is dropped on purpose, so the board must retransmit. The LCL then contains `DEMO-PN` and `TEST001`. |
| Operator Defined Download | LNL lists the fixtures. `payload.bin`, `demo.LUH`, `empty.LUH` and `traversal.LUH` are downloaded. `payload.bin` matches the reference: 4097 bytes, byte *i* = *i* mod 251. |
| Media Defined Download | LND/LNR delivers `payload.bin` byte-identical, with a completed status. |
| Upload | LUI/LUR with `demo.LUH`. The board fetches `payload.bin` from the PC, which serves the bytes it just downloaded. Status is completed (0x0003). |
| Negative | A malformed FIND is ignored and the next FIND is answered. Empty, bad and path-traversal load headers are rejected (0x1003). A corrupt payload and a truncated payload are rejected (0x1003). A valid upload afterwards succeeds. |
| Soak (optional) | `--soak N` repeats upload plus download N times. |

**Expected:** every line reads `PASS`, and the exit code is 0 (check with `echo %ERRORLEVEL%`).
Any failure prints `FAIL ...` and returns a nonzero exit code. The board must still be
running `tArinc` afterwards. Save the full console output.

### Phase F: Check the upload on the target

```c
-> arinc615aVerifyTestUpload "/sd0a/arinc_test"
```

**Expected:** `ARINC upload check PASS ...` and return value 0. This means
`upload/payload.bin` is byte-identical to the reference and no `escape.bin` was written
anywhere under the test root.

### Phase G: Lifecycle

1. Stop the loader and confirm that its task exits:

```c
-> arinc615aStop
-> taskIdVerify(taskNameToId("tArinc"))
-> i
```

   **Expected:** `arinc615aStop` returns 1 (the stop request was queued). Within a few
   seconds `tArinc` disappears from `i`, and `taskIdVerify` returns `ERROR` (-1).
2. Restart three times. Repeat each cycle: the `taskSpawn` from Phase D, then
   `python tests\vxworks_target_test.py --target <ip>`, then `arinc615aStop`. Every cycle must pass.
3. Second-instance rejection. While `tArinc` is running, start another copy:

```c
-> taskSpawn("tArinc2", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
-> i
```

   **Expected:** `tArinc2` returns an error and ends. It prints that a runtime is already
   active or that the port is in use. `tArinc` keeps working, so rerun the FIND step or
   the whole script to confirm.
4. Unload and reload. Stop the loader first, and never unload while `tArinc` exists:

```c
-> arinc615aStop
-> i                                   /* tArinc gone */
-> unld "ARINC615A.out"
-> lkup "arinc615a"                    /* expect no symbols */
-> ld < /tgtsvr/<path>/ARINC615A.out   /* reload */
-> arinc615aSelfTest                   /* expect 0 */
```

### Phase H: Resources and soak

```c
-> memShow
-> taskSpawn("tArinc", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
```

```bat
python tests\vxworks_target_test.py --target 192.168.0.3 --soak 50
```

```c
-> checkStack "tArinc"
-> memShow
```

**Expected:**

- `checkStack` shows a high-water mark well below 1 MiB and no `OVERFLOW` flag. Record the
  margin.
- The free bytes from `memShow` after the soak are within normal fluctuation of the value
  before it. Run the soak a second time and compare again: free memory must **not trend
  downward** from run to run.

### Phase I: Data loader acceptance with the ARINC-EXAMPLE CLI

This phase uses the real ARINC 615A data loader: `arinc_615a_operation.exe`, the
ARINC-EXAMPLE CLI. The script `tests\cli_acceptance.ps1` drives it through every
operation and builds an ARINC 665 media set for the upload.

**One-time CLI setup on the Windows PC** (`<EX>` is the ARINC-EXAMPLE
`arinc_615a-main` folder that holds `verify-cli.bat`):

1. Apply `tests\cli\arinc_615a_operation-exit-hang.patch` to
   `<EX>\app\arinc_615a_operation\arinc_615a_operation.cpp`. Without it the CLI never
   exits after Information, Download and Upload operations. Its command objects
   outlive the `io_context`, which hangs process exit on Windows. The results are
   printed but stay in the buffer, so they are never shown.
2. From `<EX>`, run `verify-cli.bat` to rebuild the CLI. With the published
   [ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)
   instead, run `git apply` with the patch, then `build.bat --no-run`. Its DLLs are
   in `C:\vi\x64-windows\...`, and `cli_acceptance.ps1` finds them there.
3. Build the ARINC 665 media set compiler in the same build tree:

```bat
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
<EX>\.tools\cmake-4.3.4-windows-x86_64\bin\cmake.exe --build <EX>\cmake-build-cli-verify --target arinc_665_media_set_compiler
```

4. Allow the CLI to receive UDP from the board. Run this in an elevated `cmd`, on the
   Private profile:

```bat
netsh advfirewall firewall add rule name="ARINC615A loader CLI (UDP in)" dir=in action=allow protocol=UDP profile=private program="<EX>\cmake-build-cli-verify\app\arinc_615a_operation\arinc_615a_operation.exe"
```

**Run** while `tArinc` serves `/sd0a/arinc_test/test-config.json` (Phase D):

```bat
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target 192.168.0.3 -CliBuild <EX>\cmake-build-cli-verify
```

```c
-> arinc615aVerifyTestUpload "/sd0a/arinc_test"
```

| Check | What it proves |
| --- | --- |
| C01 | `Find` discovers the board with target ID `ARINC_1` |
| C02 | `Information`: integrity valid, `DEMO-PN` shown, completed (0003) |
| C03 | `OpDownload`: file list received, `payload.bin` byte-identical, completed |
| C04 | `MedDownload`: `payload.bin` byte-identical, completed |
| C05 | ARINC 665 media set `DEMO-MS` (load `DEMOLOAD.LUH` → `payload.bin`) compiled |
| C06 | `AdhocUpload` of `DEMOLOAD.LUH`: load and operation completed |
| C07 | The board still answers `Find` after all operations |

**Expected:** 7 passed, script exit code 0. Then `arinc615aVerifyTestUpload` returns 0,
which proves the uploaded file on the board is byte-identical.

The CLI needs `--option=value` syntax. Several of its short options clash (`-l`, `-t`),
and `--target-address` otherwise swallows the next argument. For manual runs:

```bat
set PATH=<EX>\cmake-build-cli-verify\vcpkg_installed\x64-windows\debug\bin;%PATH%
arinc_615a_operation.exe -c Information --target-address=192.168.0.3 --target-id=ARINC_1 --port-option
```

Also try aborting an operation part-way with Ctrl+C. The target must accept the next
operation. For real hardware data, replace `test-config.json` with a production
`target-config.json`, as described in `START_HERE.md` §5.

## 5. Rehearsal without a board (optional)

The same entry points build into `arinc_host_runner` (see `CMakeLists.txt`). On Linux or
WSL you can rehearse Phases D to G before board time. Ports 59 and 1001 need root on
Linux, so the rehearsal moves them to 10059 and 11001:

```sh
cmake -S . -B build && cmake --build build -j8 && ctest --test-dir build
./build/arinc_host_runner --prepare /tmp/arinc
sed -i 's/"port": 59/"port": 10059/; s/"find_port": 1001/"find_port": 11001/' /tmp/arinc/test-config.json
./build/arinc_host_runner /tmp/arinc/test-config.json &    # press Enter in this shell later to stop
python3 tests/vxworks_target_test.py --target 127.0.0.1 --find-port 11001 --tftp-port 10059 --soak 5
./build/arinc_host_runner --verify /tmp/arinc
```

The Phase I CLI test runs against the same WSL target from Windows, using its IP from
`wsl hostname -I` and the moved ports. The CLI firewall rule must also allow the WSL
range (172.16.0.0/12):

```bat
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target <wsl-ip> -CliBuild <EX>\cmake-build-cli-verify -FindPort 11001 -TftpPort 10059
```

A rehearsal pass proves the procedure and scripts, not VxWorks. The board run is still mandatory.

## 6. Troubleshooting

| Symptom | Likely cause and action |
| --- | --- |
| `FAIL` at FIND: timeout | The board IP or subnet is wrong, so `ping` it first. The firewall rule is missing or the adapter is on a Public profile. `tArinc` is not running (`i`). Another service owns UDP 1001 on the board. |
| Script prints `TFTP ERROR` | Read the error text in the output. Common causes: the file is missing in `/sd0a/arinc_test/download` (rerun `arinc615aPrepareTest`), the operation is disabled in the config, or the target ID is wrong (`--target-id`). |
| TFTP transfers time out after FIND works | The PC firewall is blocking the board's transfers back to Python's ephemeral ports. Also check for more than one PC network adapter on the board subnet, or a VPN that captures the route. |
| Upload of the valid `demo.LUH` returns 0x1003 | The upload filesystem is not writable: the SD card is missing, full or read-only. Check with `devs` and `ls "/sd0a/arinc_test/upload"`, check the free space, and rerun `arinc615aPrepareTest`. |
| `arinc615aVerifyTestUpload` returns 2 or 3 | The upload never completed, or the file was altered. Check the Phase E output for the upload step. |
| `tArinc` is not in `i` right after `taskSpawn` | `arinc615aRun` returned at once. Read the console: the JSON path is wrong, the JSON is invalid, or a port is in use. Rerun `arinc615aPrepareTest` and use the exact path it prints. |
| `tArinc` is `SUSPEND`, or an exception appears on the console | The task crashed. Check for a stack overflow with `checkStack` and `tt tArinc`. Increase the stack (`0x200000`) and keep `VX_FP_TASK`. Report the exception text. |
| Unresolved symbols when loading | See `START_HERE.md` §6. Usually C++ constructor processing is missing, or POSIX or C++ components are missing from the VSB/VIP. |
| `arinc615aStop` returns 0 | No loader was running, or the stop request could not be queued. Check `i`. |

## 7. Results record

| Field | Value |
| --- | --- |
| Date / tester | |
| Board / BSP (name, version) | |
| VSB name and path | |
| VIP / kernel image identity (build date, checksum) | |
| VxWorks version (`version` in the shell) | |
| Workbench version | |
| Toolchain (LLVM version, CPU/ABI) | |
| Package source commit (`BUILD_INFO.txt`) | |
| Windows version / Python version | |
| Board IP / PC IP | |

| Test ID | Step | Expected | Result (PASS/FAIL) | Notes |
| --- | --- | --- | --- | --- |
| A-1 | Workbench Debug build | 0 errors, `.out` produced | | Attach the build log |
| B-1 | Target connection | Target server connected | | |
| B-2 | Load module | No unresolved symbols | | |
| B-3 | `lkup "arinc615a"` | All 7 entry points present | | |
| C-1 | `arinc615aSelfTest` | Returns 0, prints PASS | | |
| D-1 | `arinc615aPrepareTest` | Returns 0, fixtures listed | | |
| D-2 | `taskSpawn ... arinc615aRun` | `tArinc` running (PEND) | | |
| E-1 | FIND | PASS | | |
| E-2 | Information with a dropped packet | PASS, LCL contains DEMO-PN and TEST001 | | |
| E-3 | Operator Defined Download | PASS, payload matches reference | | |
| E-4 | Media Defined Download | PASS | | |
| E-5 | Upload | PASS, status 0x0003 | | |
| E-6 | Malformed FIND | Ignored; next FIND answered | | |
| E-7 | Empty, bad and traversal headers | Rejected with 0x1003; server alive | | |
| E-8 | Corrupt and truncated payload, then valid | Rejected, then valid PASS | | |
| E-9 | Script exit code | 0 | | Attach the output |
| F-1 | `arinc615aVerifyTestUpload` | Returns 0 | | |
| G-1 | `arinc615aStop` | Returns 1; task exits | | |
| G-2 | Restart cycle 1 | Script PASS | | |
| G-3 | Restart cycle 2 | Script PASS | | |
| G-4 | Restart cycle 3 | Script PASS | | |
| G-5 | Second concurrent start | Rejected; first instance keeps working | | |
| G-6 | `unld` and reload | Clean unload; reload and self-test pass | | |
| H-1 | `checkStack "tArinc"` | No overflow; margin recorded | | High-water mark: |
| H-2 | `--soak 50` | All PASS | | |
| H-3 | `memShow` trend | No downward trend | | Free bytes before and after: |
| I-1 | `cli_acceptance.ps1` C01 to C07 | 7 passed, exit code 0 | | Attach the output folder |
| I-2 | `arinc615aVerifyTestUpload` after the CLI upload | Returns 0 | | |
| I-3 | CLI abort (Ctrl+C) and recovery | Next operation accepted | | |

Call the port "VxWorks/board validated" only when every row (A through I) is PASS.
Keep this record with the build log, the script output, and the image and VSB identity.
