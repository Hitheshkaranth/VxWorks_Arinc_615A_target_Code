<div align="center">

<p>
  <img src="docs/images/arinc-logo.webp" alt="ARINC" height="44">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/images/vxworks-logo.png" alt="VxWorks" height="44">
</p>

# ARINC 615A Target for VxWorks 24.03

**The target side of the ARINC 615A Data Loading Protocol, as a VxWorks Downloadable Kernel Module**
Answers FIND, reports part numbers, accepts software uploads and serves downloads over Ethernet.

[![VxWorks](https://img.shields.io/badge/VxWorks-24.03-D52B1E?style=for-the-badge&logo=windriver&logoColor=white)](#setup--build-the-dkm-in-workbench)
[![Workbench](https://img.shields.io/badge/Workbench-4-D52B1E?style=for-the-badge)](#setup--build-the-dkm-in-workbench)
[![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)](https://en.cppreference.com/w/cpp/17)
[![LLVM](https://img.shields.io/badge/LLVM-17.0.6-262D3A?style=for-the-badge&logo=llvm&logoColor=white)](#office-image-compatibility)
[![Boost](https://img.shields.io/badge/Boost-1.88_bundled-F7901E?style=for-the-badge&logo=boost&logoColor=white)](third_party/DEPENDENCIES.md)

[![CPU](https://img.shields.io/badge/CPU-Cortex--A72_ARM64-0091BD?style=for-the-badge&logo=arm&logoColor=white)](#office-image-compatibility)
[![Offline](https://img.shields.io/badge/Build-100%25_offline-2EA043?style=for-the-badge)](#layer-1--host-build-and-offline-verification)
[![Tests](https://img.shields.io/badge/Host_tests-229%2F229-2EA043?style=for-the-badge)](#test-results)
[![CLI](https://img.shields.io/badge/Loader_CLI-7%2F7-2EA043?style=for-the-badge)](#layer-5--data-loader-cli-acceptance)
[![Licence](https://img.shields.io/badge/Licence-MPL--2.0-A6CE39?style=for-the-badge&logo=mozilla&logoColor=white)](LICENSE)
[![Protocol](https://img.shields.io/badge/ARINC-615A--4-1F6FEB?style=for-the-badge)](#protocol-background)

[![Tested with](https://img.shields.io/badge/Tested_with-ARINC_615A_CLI_Tool_Suite-8250DF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)
[![GUI](https://img.shields.io/badge/Also-ARINC_615A_GUI_Tool_Suite-5A6472?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Hitheshkaranth/arinc-615a-gui-tool-suite)

</div>

---

## What this is

ARINC 615A is how aircraft software gets onto, and off, the boxes on board. A
ground **data loader** talks over Ethernet to a **target**, the LRU being loaded.
The [ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)
is the loader. **This repository is the other end: the target.**

It builds the ARINC 615A **Target Hardware Application (THA)** as a VxWorks 24.03
**Downloadable Kernel Module (DKM)** for the office board: NXP Layerscape
(LS1028A), Cortex-A72, LLVM. Once loaded, the board:

- **answers FIND** so data loaders can discover it on the network,
- **reports its hardware and part numbers** (Information operation, `LCL`),
- **accepts uploads** of ARINC 665 loads, checking length and CRC before storing them,
- **serves downloads**, both media-defined and operator-defined,
- **rejects bad input** such as malformed packets, empty headers, path traversal and corrupt data, and keeps serving.

Everything needed to build it is in the repository, including Boost. There are
no downloads, no sibling repositories and no Git at build time. A ready-made
Workbench handoff lives in
[`delivery/ARINC615A_OFFICE_READY.zip`](delivery/ARINC615A_OFFICE_READY.zip).

> [!IMPORTANT]
> **Validation status.** Everything below the board has been proven: host builds,
> 229 regression cases, a VxWorks-configured compile of every source file, an audit
> of the office kernel image, and end-to-end runs against the real data loader CLI.
> **The Workbench build and the run on the physical board still have to be
> done in the office**, because the licensed SDK and the board are not available
> off-site. [`VXWORKS_TEST_PROCEDURE.md`](workbench/VXWORKS_TEST_PROCEDURE.md)
> is the checklist that closes that gap. See [VALIDATION.md](VALIDATION.md).

---

## Quick start — one command

From nothing to a built, fully checked target, in one line:

**Linux** (installs any missing tools; verified on Ubuntu, Debian, Fedora, Arch
and openSUSE)

```bash
git clone https://github.com/Hitheshkaranth/VxWorks_Arinc_615A_target_Code.git && cd VxWorks_Arinc_615A_target_Code && ./setup.sh
```

**Windows** (`cmd`; builds through WSL, then run `wsl --install` once if WSL is missing)

```bat
git clone https://github.com/Hitheshkaranth/VxWorks_Arinc_615A_target_Code.git && cd VxWorks_Arinc_615A_target_Code && setup.bat
```

That builds everything offline and runs the 229-case regression suite, the
VxWorks preflight (129/129 files) and the dependency audit. It takes about four
minutes the first time.

| Platform | Status of the one-liner |
| --- | --- |
| Ubuntu 24.04 · Ubuntu 22.04 · Fedora 41 | ✅ verified from bare Docker images. On 22.04 it also fetched CMake 3.31.6 |
| Debian 12 · Arch · openSUSE Tumbleweed | ✅ verified from bare Docker images, cloning from GitHub (GCC 12 to 16, CMake 3.25 to 4.4) |
| WSL Ubuntu · Windows 11 (`setup.bat`) | ✅ verified |

On every Linux image, verified means the tools installed, the build succeeded, all
checks passed and the rehearsal ran 9/9 (target, protocol peer, upload check,
clean stop).

### One-line usage

| What | Linux | Windows |
| --- | --- | --- |
| Build and run all host checks | `./setup.sh` | `setup.bat` |
| Rehearse: local target + protocol peer + upload check | `./setup.sh rehearse` | `setup.bat rehearse` |
| Run the target on this PC (Enter stops it) | `./setup.sh run` | `setup.bat run` |
| Test a running target, e.g. the board | `./setup.sh test 192.168.0.3` | `setup.bat test 192.168.0.3` |
| Test it with the ARINC 615A CLI Tool Suite | — | `setup.bat cli 192.168.0.3 <cli-build>` |
| Help | `./setup.sh help` | `setup.bat help` |

`run` prints the exact `test` and `cli` commands for the target it started. As a
normal user it moves the ports to 11001/10059, because Linux reserves ports below
1024 for root. Add `--find-port 11001 --tftp-port 10059` to `test`, and
`-FindPort 11001 -TftpPort 10059` to `cli`. On Windows, `test` and `cli` run natively
(Python and PowerShell) so the board's TFTP transfers reach them; only the
build goes through WSL.

Then take `delivery/ARINC615A_OFFICE_READY.zip` to Workbench, see
[Setup — build the DKM in Workbench](#setup--build-the-dkm-in-workbench).

---

## ARINC 615A in brief

ARINC 615A-4 (*Software Data Loader Using Ethernet Interface*) defines how a
**data loader** (DL) moves software and data to and from **target hardware** over
Ethernet. It has two parts:

- **FIND** (*FIND Identification of Network Devices*): a UDP broadcast on port
  **1001**. The loader asks "who is out there?" (IRQ), and every target answers
  with its identity (IAN): hardware ID, type, position, name and manufacturer.
- **The Data Load Protocol (DLP)**: every operation is a series of small
  **protocol files** exchanged over **TFTP** on UDP port **59**. There are no
  commands and no sessions, only files whose extension says what they mean.

```mermaid
flowchart LR
    DL["<b>Data loader</b><br/>ground side<br/><i>CLI Tool Suite · portable DL · bench tool</i>"]
    TH["<b>Target hardware</b><br/>LRU on the aircraft<br/><i>this repository · THA on VxWorks</i>"]
    DL -->|"① FIND IRQ · UDP 1001 broadcast"| TH
    TH -->|"② FIND IAN · who I am"| DL
    DL -->|"③ read  TARGET.xxI · start an operation"| TH
    TH -->|"④ write status files · progress"| DL
    DL <-->|"⑤ loads / files · TFTP UDP 59"| TH
    TH -->|"⑥ final status · 0003 Completed"| DL

    classDef dl fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef th fill:#238636,stroke:#116329,color:#fff
    class DL dl
    class TH th
```

### The four operations

| Operation | Starts with | What it does | Typical use |
| --- | --- | --- | --- |
| **Information** | `<ID>.LCI` | Target sends its configuration list `LCL`: hardware, serial number, part numbers | Confirm what software is installed before or after a load |
| **Upload** | `<ID>.LUI` | Loader sends a list of loads (`LUR`); the target pulls each ARINC 665 load header (`.LUH`) and its files | Install new software or data on the LRU |
| **Media Defined Download** | `<ID>.LND` | Loader names the files it wants (`LNR`); the target sends them | Retrieve known files such as logs or configuration |
| **Operator Defined Download** | `<ID>.LNO` | Target offers a list (`LNL`), the operator picks from it (`LNA`), the target sends them | Browse and retrieve whatever the target offers |

`<ID>` is the **target ID** (`ARINC_1` here). Status files (`LUS`, `LNS`) carry a
counter, a progress ratio, an exception timer and one of these codes:

| Code | Meaning | | Code | Meaning |
| --- | --- | --- | --- | --- |
| `0001` | Operation accepted | | `1000` | Operation denied |
| `0002` | In progress | | `1002` | Not supported by the target |
| `0003` | **Completed** | | `1003` | Aborted by the target hardware |
| `0004` | In progress, with description | | `1004` / `1005` | Aborted by the data loader / the operator |

**Software loads** travel as **ARINC 665** media sets: a load header (`.LUH`)
lists the load's part number, the target hardware it is for, and every data file
with its length and CRC. The target uses that header to check what it received.

---

## How it fits together

```mermaid
flowchart LR
    subgraph GROUND["🖥️  Windows PC — ground side"]
        direction TB
        CLI["<b>arinc_615a_operation.exe</b><br/>ARINC 615A CLI Tool Suite<br/><i>the real data loader</i>"]
        PS["<b>tests/cli_acceptance.ps1</b><br/><i>drives the CLI · 7 checks</i>"]
        PY["<b>tests/vxworks_target_test.py</b><br/><i>independent peer · 9 checks</i>"]
        WB["<b>Workbench 4</b><br/><i>build · load · debug</i>"]
        PS --> CLI
    end

    subgraph BOARD["✈️  VxWorks 24.03 board — target side"]
        direction TB
        SHELL["kernel shell<br/><i>arinc615a* entry points</i>"]
        DKM["<b>ARINC 615A DKM</b><br/>task tArinc · arinc615aRun"]
        FS["/sd0a/arinc_test<br/><i>upload · download · config</i>"]
        SHELL --> DKM
        DKM <--> FS
    end

    CLI <-->|"UDP 1001 · FIND"| DKM
    CLI <-->|"UDP 59 · TFTP · 615A files"| DKM
    PY <-->|"UDP 1001 / 59"| DKM
    WB -->|"target server · .out"| SHELL

    classDef ground fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef board fill:#238636,stroke:#116329,color:#fff
    classDef tool fill:#8250DF,stroke:#5A32A3,color:#fff
    class CLI,WB ground
    class PS,PY tool
    class SHELL,DKM,FS board
```

The loader starts every conversation. The target listens on **UDP 1001** (FIND)
and **UDP 59** (data load, not the usual TFTP port 69), then opens TFTP transfers
back to the loader for status and data files. Every operation is a set of
**files** moved over TFTP; only FIND is a plain request and answer.

### Inside the module

```mermaid
flowchart TB
    subgraph DKM["ARINC 615A DKM · 129 C++17 translation units"]
        direction TB
        EP["<b>workbench/EntryPoints.cpp · TestSupport.cpp</b><br/><i>C entry points for the kernel shell</i>"]
        THA["<b>THA application</b><br/>app/arinc_615a_unit_test/arinc_615a_test_tha<br/><i>JSON config · operation wiring</i>"]
        TGT["<b>lib/arinc_615a/target</b><br/><i>Information · Upload · Media/Operator Download state machines</i>"]
        FIND["<b>lib/arinc_615a/find</b><br/><i>FIND server · IRQ/IAN</i>"]
        FILES["<b>lib/arinc_615a/files</b><br/><i>LCI LCL LUI LUR LUS LND LNO LNL LNA LNS…</i>"]
        A665["<b>third_party/arinc_665</b><br/><i>load header parse · CRC checks</i>"]
        TFTP["<b>lib/tftp</b><br/><i>client · server · 615A options</i>"]
        ASIO["<b>Boost.Asio</b> · select reactor<br/><i>socket wake-up, no pipe()</i>"]
        EP --> THA --> TGT
        THA --> FIND
        TGT --> FILES --> TFTP
        TGT --> A665
        FIND --> ASIO
        TFTP --> ASIO
    end
    ASIO -->|"sockLib · selectLib · IPNET"| NET["VxWorks network stack"]

    classDef mine fill:#0B5CA8,stroke:#083F73,color:#fff
    classDef os fill:#5A6472,stroke:#3D4551,color:#fff
    class EP,THA,TGT,FIND,FILES,A665,TFTP,ASIO mine
    class NET os
```

---

## Architecture in detail

The diagrams below follow the code: `app/arinc_615a_unit_test/arinc_615a_test_tha/arinc_615a_test_tha.cpp`
(runtime and dispatch), `TargetUploadOperation.cpp` (upload checks),
`lib/arinc_support/BuildConfig.hpp` (VxWorks adaptation) and `tools/prepare_office.py`
(packaging). The ground side in every diagram is the
**[ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)**
(`arinc_615a_operation.exe`), the data loader used to test this target.

### 1 · Task and event-loop model

The module creates **no threads of its own**. `arinc615aRun` builds one
`boost::asio::io_context`, registers the FIND server and the ARINC 615A target
protocol on it, and runs it **inside the calling task**, `tArinc`. Every
callback, timer and TFTP transfer runs one at a time on that task, so the
protocol code needs no locks. Stopping is a message into the event loop, not a
kill.

```mermaid
flowchart TB
    subgraph SHELL["kernel shell / any other task"]
        SPAWN["taskSpawn tArinc … arinc615aRun(json)"]
        STOP["arinc615aStop()"]
    end

    subgraph TASK["task tArinc · 1 MiB stack · VX_FP_TASK"]
        direction TB
        CFG["runFromFile(json)<br/><i>parse JSON → TargetDataLoaderConfiguration</i>"]
        GUARD{"another runtime<br/>already active?"}
        RT["Runtime.run()"]
        subgraph LOOP["io_context.run() · single-threaded event loop"]
            direction LR
            FS["FIND server<br/><i>UDP 1001</i>"]
            PR["Target protocol<br/><i>TFTP server · UDP 59</i>"]
            OPS["active operation<br/><i>at most one</i>"]
            PR --> OPS
        end
        END(["return 0 · task exits"])
        CFG --> GUARD
        GUARD -->|no| RT --> LOOP
        LOOP -->|"io_context.stop()"| END
    end
    GUARD -->|yes| REJ(["return error · 'already running'<br/><i>first runtime keeps serving</i>"])

    SPAWN --> CFG
    STOP -->|"requestStop(): post(stop) into the loop"| LOOP
    LOOP -. "stop(): findServer.stop · protocol.stop · io_context.stop" .-> END

    classDef task fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef loop fill:#238636,stroke:#116329,color:#fff
    classDef bad fill:#9E6A03,stroke:#7D4E00,color:#fff
    class CFG,RT task
    class FS,PR,OPS loop
    class REJ bad
```

**Why this matters on VxWorks.** One task means one stack to size (`checkStack`),
and nothing is left running after `arinc615aRun` returns, so `unld` is safe once
`tArinc` has gone. `arinc615aStop` is safe to call from any task: it only posts
a message, and the stop itself runs inside `tArinc`.

### 2 · Request dispatch

Every data-load request, whichever operation it is, arrives as a TFTP read of an
initialisation file (`<TARGET_ID>.LCI`, `.LUI`, `.LND` or `.LNO`) and goes
through one gate, `Runtime::operationRequest`. A request that fails the gate
still gets a proper ARINC 615A answer: an **error operation** that returns
*Operation Denied* or *Not Supported* instead of silence.

```mermaid
flowchart TD
    REQ(["Loader reads TARGET_ID.xxI<br/><i>UDP 59 · TFTP RRQ</i>"]) --> ID{"target ID in<br/>targets_configuration?"}
    ID -->|no| E1["ErrorOperation<br/><b>Operation Denied</b>"]
    ID -->|yes| BUSY{"operation already<br/>active?"}
    BUSY -->|yes| E2["ErrorOperation<br/><b>Denied</b> · 'Another operation already active'"]
    BUSY -->|no| TYPE{"operation type"}
    TYPE -->|LCI| INF["Information"]
    TYPE -->|LUI| UPL["Upload"]
    TYPE -->|LND| MDD["Media Defined Download"]
    TYPE -->|LNO| ODD["Operator Defined Download"]
    TYPE -->|other| E3["ErrorOperation<br/><b>Not Supported</b>"]
    INF & UPL & MDD & ODD --> EN{"enabled in<br/>JSON config?"}
    EN -->|no| E4["ErrorOperation<br/><b>Denied</b> · 'not Enabled'"]
    EN -->|yes| RUN(["operation started<br/><i>initialisation answer 0001 Accepted</i>"])

    classDef ok fill:#238636,stroke:#116329,color:#fff
    classDef err fill:#DA3633,stroke:#A40E26,color:#fff
    classDef op fill:#1F6FEB,stroke:#0D419D,color:#fff
    class RUN ok
    class E1,E2,E3,E4 err
    class INF,UPL,MDD,ODD op
```

### 3 · Protocol file exchange per operation

ARINC 615A is file-driven. The loader starts each operation by *reading* an
initialisation file from the target. After that, the **target** pushes status
files to the loader, and whichever side owns the data sends it. `(P)` marks the
files that use the port the loader advertised with `--port-option`.

```mermaid
sequenceDiagram
    autonumber
    participant L as Loader<br/>(CLI Tool Suite)
    participant T as Target (tArinc)

    rect rgb(230, 240, 255)
    Note over L,T: Information
    L->>T: read  ARINC_1.LCI
    T-->>L: LCI · 0001 Accepted
    T->>L: write ARINC_1.LCL (P) · hardware + part numbers
    end

    rect rgb(230, 255, 235)
    Note over L,T: Upload
    L->>T: read  ARINC_1.LUI
    T->>L: write ARINC_1.LUS (P) · 0001 Accepted
    L->>T: write ARINC_1.LUR · list of load headers
    T->>L: read  DEMOLOAD.LUH (P)
    T->>L: read  payload.bin (P) · for every data file in the header
    T->>L: write ARINC_1.LUS (P) · 0002 … then 0003 Completed
    end

    rect rgb(255, 245, 225)
    Note over L,T: Media Defined Download
    L->>T: read  ARINC_1.LND
    T->>L: write ARINC_1.LNS (P) · Accepted
    L->>T: write ARINC_1.LNR · requested files
    T->>L: write payload.bin (P)
    T->>L: write ARINC_1.LNS (P) · 0003 Completed
    end

    rect rgb(245, 235, 255)
    Note over L,T: Operator Defined Download
    L->>T: read  ARINC_1.LNO
    T->>L: write ARINC_1.LNL (P) · files available
    L->>T: write ARINC_1.LNA · operator's selection
    T->>L: write payload.bin (P)
    T->>L: write ARINC_1.LNS (P) · 0003 Completed
    end
```

| Operation | Init file (loader reads) | Loader writes | Target writes | Final status |
| --- | --- | --- | --- | --- |
| Information | `LCI` | — | `LCL` | Completed with the `LCL` |
| Upload | `LUI` | `LUR`, then serves `.LUH` + data files | `LUS` (repeated) | `LUS` 0003 |
| Media Defined Download | `LND` | `LNR` | `LNS`, requested files | `LNS` 0003 |
| Operator Defined Download | `LNO` | `LNA` | `LNL`, `LNS`, selected files | `LNS` 0003 |

Download sources come from the configured download directory; uploads land in
the configured upload directory. Both are set per target in the JSON config.

### 4 · Upload validation pipeline

An upload is only accepted if **the bytes stored on the target's disk** match
what the load header promises. The check runs on the stored file, not on the
data received over the network, so a filesystem write error is caught too.

```mermaid
flowchart TD
    A(["LUR received · load list"]) --> B["fetch LUH from the loader"]
    B --> C{"LUH parses as an<br/>ARINC 665 load header<br/>with ≥ 1 data file?"}
    C -->|"no · empty or malformed"| X1["abort · 0x1003<br/><i>'Invalid Load Header' ·<br/>'does not contain data files'</i>"]
    C -->|yes| D{"every data-file name safe?<br/><i>not empty · not . or ..<br/>no / \ or :</i>"}
    D -->|"no · path traversal"| X2["abort · 'Invalid load filename'<br/><i>nothing written</i>"]
    D -->|yes| E["for each data and support file:<br/>TFTP read into upload directory<br/><i>expected length · CRC16 · check value from the header</i>"]
    E --> F{"stored file on disk:<br/>length = header length<br/>CRC16 = header CRC<br/>check value matches?"}
    F -->|no| X3["LoadPartNumberOrDownloadFileFailed<br/>abort · 'Stored file size/checksum mismatch'"]
    F -->|yes| G{"more files?"}
    G -->|yes| E
    G -->|no| H(["loadFinished · LUS 0003 Completed"])

    classDef ok fill:#238636,stroke:#116329,color:#fff
    classDef err fill:#DA3633,stroke:#A40E26,color:#fff
    classDef step fill:#1F6FEB,stroke:#0D419D,color:#fff
    class H ok
    class X1,X2,X3 err
    class B,E step
```

Each rejection branch is exercised by a test: T07 (empty, malformed and
path-traversal headers) and T08 (corrupt and truncated payloads) in
[`vxworks_target_test.py`](tests/vxworks_target_test.py), and `arinc615aVerifyTestUpload`
confirms afterwards that no `escape.bin` ever reached the disk.

### 5 · VxWorks adaptation layer

Almost all of the code is plain, portable C++17. Everything VxWorks-specific is
concentrated in one force-included header and one Boost overlay, so the
protocol code never tests for the platform.

```mermaid
flowchart LR
    subgraph SRC["every translation unit"]
        FI["<b>-include arinc_support/BuildConfig.hpp</b>"]
    end

    subgraph BC["BuildConfig.hpp · only when __VXWORKS__"]
        direction TB
        H["vxWorks.h · sockLib.h · ioLib.h · sysLib.h · selectLib.h"]
        U["#undef m_data<br/><i>mbuf.h macro vs Boost.PropertyTree</i>"]
        K["#error unless _WRS_KERNEL<br/><i>DKM, never RTP</i>"]
        P["BOOST_PLATFORM_CONFIG → BoostVxWorks.hpp"]
        R["disable epoll · kqueue · /dev/poll<br/>serial ports · local sockets"]
        S["ARINC_ASIO_SOCKET_SELECT_INTERRUPTER"]
    end

    subgraph OV["Boost.Asio · bundled 1.88 + overlay"]
        direction TB
        SEL["select reactor"]
        INT["socket_select_interrupter<br/><i>loopback TCP pair instead of pipe()</i>"]
        POLL["poll() → select() shim"]
        SP["socketpair → not supported"]
    end

    subgraph IMG["office kernel image components"]
        direction TB
        C1["INCLUDE_SOCKLIB · IPNET"]
        C2["INCLUDE_SELECT"]
        C3["INCLUDE_POSIX_PTHREADS · CLOCKS"]
        C4["INCLUDE_CPLUS · LIBCPLUS_STD<br/><i>C++17 · std::filesystem</i>"]
        C5["INCLUDE_DOSFS · SD"]
    end

    FI --> BC
    S --> INT
    R --> SEL
    SEL --> C2
    INT --> C1
    POLL --> C2
    H --> C1
    BC -.-> C3
    BC -.-> C4
    BC -.->|"uploads · downloads via std::filesystem"| C5

    classDef cfg fill:#0B5CA8,stroke:#083F73,color:#fff
    classDef asio fill:#8250DF,stroke:#5A32A3,color:#fff
    classDef img fill:#5A6472,stroke:#3D4551,color:#fff
    class FI,H,U,K,P,R,S cfg
    class SEL,INT,POLL,SP asio
    class C1,C2,C3,C4,C5 img
```

The preflight ([layer 2](#layer-2--vxworks-preflight)) checks this layer on
every build. It asserts the select reactor, the socket interrupter and the
`selectLib.h` include chain, and its stub `sockLib.h` defines `m_data`, so a
missing `#undef` fails the check.

### 6 · Build and delivery pipeline

```mermaid
flowchart LR
    subgraph REPO["this repository"]
        direction TB
        SRCS["lib · app · workbench<br/><i>C++17 sources</i>"]
        TAR["boost_1_88_0_headers.tar.gz<br/><i>SHA-256 pinned</i>"]
        OVL["boost_vxworks_overlay"]
    end

    subgraph HOST["host build · Linux / WSL"]
        direction TB
        BB["BundledBoost.cmake<br/><i>extract → overlay → Asio patches</i>"]
        T1["ctest · 229 cases"]
        T2["preflight · 129/129"]
        T3["target audit"]
        GEN["tools/prepare_office.py"]
        BB --> T1 & T2 & T3
        T1 & T2 & T3 --> GEN
    end

    subgraph PKG["ARINC615A_OFFICE_READY.zip"]
        direction TB
        PSRC["src/ · 129 files · SOURCES.txt"]
        PINC["include/ · expanded Boost headers"]
        PDOC["START_HERE · BUILD_OPTIONS<br/>VXWORKS_TEST_PROCEDURE"]
        PT["tests/ · Python peer · CLI script · patch"]
        PSUM["SHA256SUMS · BUILD_INFO<br/><i>source commit</i>"]
    end

    subgraph OFFICE["office · Windows"]
        direction TB
        WBD["Workbench 4<br/>DKM project · LLVM"]
        OUT["ARINC615A.out"]
        BRD["LS1028A board<br/>VxWorks 24.03"]
        WBD --> OUT -->|"ld · target server"| BRD
    end

    SRCS & TAR & OVL --> BB
    GEN --> PKG
    PKG --> WBD
    PT -.->|"layers 4 and 5"| BRD

    classDef repo fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef host fill:#8250DF,stroke:#5A32A3,color:#fff
    classDef pkg fill:#9E6A03,stroke:#7D4E00,color:#fff
    classDef office fill:#238636,stroke:#116329,color:#fff
    class SRCS,TAR,OVL repo
    class BB,T1,T2,T3,GEN host
    class PSRC,PINC,PDOC,PT,PSUM pkg
    class WBD,OUT,BRD office
```

The office machine needs no Python, CMake, Git or internet: the ZIP carries
expanded headers and an explicit source list. `BUILD_INFO.txt` records the
source commit, and `SHA256SUMS.txt` lets the office check that nothing changed in
transit.

---

## Shell entry points

The module exports plain C functions, so everything is driven from the VxWorks
kernel shell (C interpreter) or from a Workbench debug launch.

| Function | Returns | Purpose |
| --- | --- | --- |
| `arinc615aSelfTest()` | `0` = pass | Codec and SHA-256 self-test. No network or storage needed |
| `arinc615aDemo()` | on stop | FIND + Information demo with built-in defaults; **blocks** its task |
| `arinc615aRun(const char *json)` | on stop | Full target from a JSON config; **blocks** its task |
| `arinc615aStop()` | `1` = queued | Ask a running `arinc615aRun`/`arinc615aDemo` to stop (call from another task) |
| `arinc615aPrepareTest(const char *root)` | `0` = ok | Create `root/upload`, `root/download` fixtures and `root/test-config.json` |
| `arinc615aVerifyTestUpload(const char *root)` | `0` = pass | Check the uploaded `payload.bin` is byte-identical and nothing escaped the upload folder |
| `arinc615aWriteFixtures(const char *dir)` | `0` = ok | Write only the four test fixtures into `dir` |

Defaults used by the demo and the test config: **FIND port 1001**, **TFTP port 59**,
**target ID `ARINC_1`**, hardware ID `ARINC`, part number `DEMO-PN`, serial `TEST001`.

---

## Office image compatibility

The code was audited against the office's exported projects
(`UVDR_VIP_20260218`, `UVDR_VSB_20260218`, BSP `nxp_layerscape_a72_2_0_7_4`, LLVM,
`CORTEX_A72`). Every C and POSIX function the module calls was looked up in the
VSB library symbol tables, and every owning component was checked in the kernel
image. The gaps this found are fixed in the code, so the module works on the
**image as it is**, with no kernel rebuild:

| The image lacks | Would have caused | Fix in this repository |
| --- | --- | --- |
| `INCLUDE_POSIX_PIPES` → no `pipe()` | Unresolved `pipe` at `ld`; the module never loads | Boost.Asio uses its loopback-socket wake-up (`ARINC_ASIO_SOCKET_SELECT_INTERRUPTER`, set in `BuildConfig.hpp`) |
| `pthread_rwlock_*` (not in the VSB) | Unresolved at load or compile | Statistics classes use `std::mutex` instead of `std::shared_mutex` |
| `poll()` (not linked into the image) | Unresolved `poll` | `poll()` shim over `select()` in the bundled Asio overlay |
| `socketpair()` (not declared) | Compile error | Asio's `socketpair` reports unsupported, as on Windows (local sockets are disabled) |
| `m_data` macro from `mbuf.h` | Boost.PropertyTree compile errors | `#undef m_data` in `BuildConfig.hpp` right after the VxWorks headers |
| A RAM disk (`/ram0` does not exist) | Upload/download paths fail | Configs and tests use the SD card: `/sd0a/...` |

Present and used: C++ with exceptions and RTTI, the Dinkumware C++17 library
including `std::filesystem`, pthreads, clocks, `select`, IPv4 sockets, DOSFS on
SD, loader and unloader, `memShow` and `checkStack`.

The Boost fixes live in [`third_party/boost_vxworks_overlay`](third_party/boost_vxworks_overlay)
and are applied by [`cmake/BundledBoost.cmake`](cmake/BundledBoost.cmake), so a
regenerated package always carries them.

---

## Setup — build the DKM in Workbench

### Prerequisites

| | Needed |
| --- | --- |
| Host | Windows PC with **Wind River Workbench 4** and the office **VxWorks 24.03 SDK** |
| Target image | The office VIP/VSB (or any image with the components above) running on the board |
| Network | PC and board on the same IPv4 subnet; UDP **59** and **1001** open |
| Storage | A writable DOSFS partition on the board, e.g. `/sd0a` |
| For testing | Python 3.8+ and the [ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite) |

### Steps

```mermaid
flowchart LR
    Z(["ARINC615A_OFFICE_READY.zip"]) --> X["Extract to a short path<br/><i>C:\ARINC\ARINC615A_OFFICE_READY</i>"]
    X --> P["New project in Workbench:<br/><b>VxWorks Downloadable Kernel Module</b>"]
    P --> O["Set options from<br/><b>BUILD_OPTIONS.txt</b>"]
    O --> I["Build input: <b>src/ only</b><br/><i>129 files in SOURCES.txt</i>"]
    I --> B["Build Debug"]
    B --> OUT(["<b>ARINC615A.out</b>"])

    classDef ok fill:#238636,stroke:#116329,color:#fff
    classDef step fill:#1F6FEB,stroke:#0D419D,color:#fff
    class Z,OUT ok
    class X,P,O,I,B step
```

1. **Extract** `delivery/ARINC615A_OFFICE_READY.zip` to a short local path.
2. In Workbench, create a **VxWorks Downloadable Kernel Module** project (not RTP)
   on platform **vxworks/24.03** with **CORTEX_A72 / ARM64** and **LLVM 17.0.6.1**.
   Use the **same VSB and BSP as the running board image**. Remove any
   wizard-generated sample source.
3. **Build options.** Copy them from `BUILD_OPTIONS.txt`:

   ```text
   -std=c++17  -g  -O0  -fexceptions  -frtti  -include arinc_support/BuildConfig.hpp

   Include directories:  include   src/lib   src/workbench
                         src/app/arinc_615a_unit_test/arinc_615a_test_tha
   ```

4. **Build input.** Compile only `src/`. Exclude `include/`, `tests/` and the
   top-level `workbench/`. `SOURCES.txt` in the package is the exact list of
   129 files.
5. **Build Debug.** Keep the first build log word for word if anything fails;
   `START_HERE.md` §6 lists the likely first-build errors and their fixes.

> [!WARNING]
> Build with `-std=c++17`, **not** C++20. The 24.03 LLVM 17 runtime does not
> provide the C++20 library features, and the code deliberately avoids them.

Full walkthrough: [`workbench/START_HERE.md`](workbench/START_HERE.md).

---

## Runtime — load and run on the board

Type these in the kernel shell, at the `->` prompt.

### 1. Load and self-test

```c
-> ld < /tgtsvr/<path-below-tgtsvr-root>/ARINC615A.out   /* or Workbench: Download */
-> lkup "arinc615a"                                      /* 7 entry points listed */
-> arinc615aSelfTest
ARINC self-test PASS (codecs and SHA256; network/storage tested separately)
value = 0 = 0x0
```

The load must report **no unresolved symbols**.

### 2. Prepare the test root and start the target

```c
-> devs                                   /* confirm /sd0a is mounted */
-> arinc615aPrepareTest "/sd0a/arinc_test"
ARINC test prepared. Start the loader with config /sd0a/arinc_test/test-config.json
-> taskSpawn("tArinc", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
-> i                                      /* tArinc is PEND, waiting on the network */
```

`0x01000000` is `VX_FP_TASK`, and `0x100000` gives the task a 1 MiB stack.
`arinc615aRun` blocks, so it always runs in its own task.

### 3. Stop, restart, unload

```c
-> arinc615aStop                          /* returns 1 = stop queued */
-> i                                      /* tArinc has exited */
-> unld "ARINC615A.out"                   /* never while tArinc exists */
```

### Lifecycle

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Loaded: ld < ARINC615A.out
    Loaded --> Loaded: arinc615aSelfTest → 0
    Loaded --> Prepared: arinc615aPrepareTest root
    Prepared --> Serving: taskSpawn … arinc615aRun
    Serving --> Serving: FIND · Information · Upload · Downloads
    Serving --> Stopped: arinc615aStop
    Stopped --> Serving: taskSpawn again
    Stopped --> [*]: unld
    Serving --> Serving: second arinc615aRun rejected
```

### Configuration

`arinc615aRun` reads a JSON file. The sample [`target-config.json`](workbench/target-config.json)
enables every operation:

```json
{
  "version": "Arinc615a34",
  "arinc_615a":      { "local_tftp_address": "0.0.0.0", "tftp": { "port": 59, "timeout": 3, "retries": 3 } },
  "arinc_615a_find": { "local_find_address": "0.0.0.0", "find_port": 1001 },
  "targets_configuration": [{
    "target_id": "ARINC_1",
    "information_operation":               { "enabled": true, "...": "hardware + part numbers" },
    "upload_operation":                    { "enabled": true, "directory": "/sd0a/ARINC/upload" },
    "media_defined_download_operation":    { "enabled": true, "directories": { "directory": "/sd0a/ARINC/download" } },
    "operator_defined_download_operation": { "enabled": true, "directories": { "directory": "/sd0a/ARINC/download" } }
  }]
}
```

Replace the demo part numbers with real hardware data, and point the
directories at **target** paths, not Windows paths.

---

## Connecting a real target to the CLI tool

This section connects the board running this module to the
**[ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)**
on a Windows PC. The addresses and interfaces are those of the office image
(`UVDR_VIP_20260218`). Its default boot line is
`memac(0,0)host:vxWorks h=192.168.0.2 e=192.168.0.3`.

### Physical setup

```mermaid
flowchart LR
    subgraph PC["🖥️  Windows PC · 192.168.0.2/24"]
        direction TB
        CLI["<b>arinc_615a_operation.exe</b><br/>CLI Tool Suite<br/><i>FIND · Information · Upload · Downloads</i>"]
        SCR["tests/cli_acceptance.ps1"]
        WB["Workbench 4<br/><i>build · download .out · debug</i>"]
        TERM["Serial terminal<br/><i>PuTTY / Tera Term · COMx</i>"]
        NIC1["Ethernet NIC<br/><i>static IP · Private profile</i>"]
        USB["USB-UART"]
        SCR --> CLI
        CLI --> NIC1
        WB --> NIC1
        TERM --> USB
    end

    SW{{"Ethernet<br/>direct cable or<br/>maintenance switch"}}

    subgraph BRD["✈️  LS1028A board · VxWorks 24.03 · 192.168.0.3/24"]
        direction TB
        ETH["memac0<br/><i>IP from boot line e=</i>"]
        UART["/ttyS0<br/><i>115200 8N1 · kernel shell</i>"]
        DKM["<b>ARINC 615A DKM</b><br/>tArinc · FIND 1001 · TFTP 59"]
        SD["SD card<br/><i>/sd0a/arinc_test</i>"]
        ETH --> DKM
        UART --> DKM
        DKM --> SD
    end

    NIC1 <-->|"UDP 1001 · UDP 59<br/>+ TFTP data ports"| SW <--> ETH
    USB <-->|"serial console"| UART

    classDef pc fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef brd fill:#238636,stroke:#116329,color:#fff
    classDef net fill:#8250DF,stroke:#5A32A3,color:#fff
    class CLI,SCR,WB,TERM,NIC1,USB pc
    class ETH,UART,DKM,SD brd
    class SW net
```

Two links, two jobs:

- **Ethernet** carries ARINC 615A: FIND on UDP 1001, the data load on UDP 59, and
  the TFTP transfers the board opens back to the PC. Workbench uses it too.
- **Serial** is the kernel shell, used to load, start and check the module. The
  image has **no telnet server**, so the console is the shell.

### Address plan

| | PC | Board |
| --- | --- | --- |
| IPv4 | `192.168.0.2/24` (boot-line host `h=`) | `192.168.0.3/24` (boot-line target `e=`) |
| Interface | the PC's Ethernet NIC | `memac0` |
| Listens on | TFTP data ports opened by the CLI | UDP **1001** (FIND), UDP **59** (TFTP) |
| Console | COM port · 115200 8N1 | `/ttyS0` |

> [!NOTE]
> The board's IP comes from its **boot line**, not from the shell. The image does
> not include the `ifconfig` shell command. To use another address, change `e=` in
> the boot parameters and reboot, or rebuild the VIP with a new `DEFAULT_BOOT_LINE`.
> Keep the PC and the board in the same subnet: FIND is a broadcast and does not
> cross routers.

### Bring-up, step by step

```mermaid
flowchart TD
    A(["1 · Cable Ethernet + serial, power on"]) --> B{"serial console shows<br/>the VxWorks banner and -> ?"}
    B -->|no| BF["check COM port · 115200 8N1 · cable"]
    B -->|yes| C["2 · PC static IP 192.168.0.2/24"]
    C --> D{"3 · ping 192.168.0.3<br/>from the PC?"}
    D -->|no| DF["check cable/link LEDs · boot line e= ·<br/>PC adapter and subnet"]
    D -->|yes| E["4 · firewall rule for the CLI"]
    E --> F["5 · load module · self-test"]
    F --> G["6 · prepare test root · taskSpawn tArinc"]
    G --> H{"7 · CLI Find sees ARINC_1?"}
    H -->|no| HF["tArinc running? (i) · UDP 1001 blocked? ·<br/>wrong subnet?"]
    H -->|yes| I{"8 · CLI Information completes?"}
    I -->|no| IF["PC firewall blocks the board's<br/>TFTP transfers back to the CLI"]
    I -->|yes| J(["9 · cli_acceptance.ps1 · 7/7"])

    classDef ok fill:#238636,stroke:#116329,color:#fff
    classDef err fill:#DA3633,stroke:#A40E26,color:#fff
    classDef step fill:#1F6FEB,stroke:#0D419D,color:#fff
    class J ok
    class BF,DF,HF,IF err
    class C,E,F,G step
```

**1 · Cable and console.** Connect the board's Ethernet port to the PC (direct or
through a switch) and the board's console UART to the PC. Open the COM port at
**115200 8N1** and power on. You should see the VxWorks banner and the `->`
prompt.

**2 · Give the PC its address.** In an elevated `cmd`, using the adapter name
shown by `ipconfig`:

```bat
netsh interface ipv4 set address name="Ethernet" static 192.168.0.2 255.255.255.0
```

**3 · Check the link.** There is no `ping` command on the board, so check from
the PC:

```bat
ping 192.168.0.3
```

**4 · Let the board's transfers reach the CLI.** The board opens TFTP transfers
*to* the PC, so Windows Firewall must allow them. Run once, elevated:

```bat
netsh advfirewall firewall add rule name="ARINC615A loader CLI (UDP in)" dir=in action=allow protocol=UDP profile=private remoteip=192.168.0.0/24 program="<cli-build>\app\arinc_615a_operation\arinc_615a_operation.exe"
```

**5–6 · Load and start the target.** In the serial console:

```c
-> ld < /tgtsvr/<path>/ARINC615A.out      /* or Workbench: Download */
-> arinc615aSelfTest                      /* value = 0 */
-> arinc615aPrepareTest "/sd0a/arinc_test"
-> taskSpawn("tArinc", 100, 0x01000000, 0x100000, arinc615aRun, "/sd0a/arinc_test/test-config.json")
-> i                                      /* tArinc is PEND */
```

**7–8 · Talk to it with the CLI.** On the PC, with the CLI's DLLs on `PATH`:

```bat
arinc_615a_operation.exe -c Find
arinc_615a_operation.exe -c Find        --target-address=192.168.0.3
arinc_615a_operation.exe -c Information --target-address=192.168.0.3 --target-id=ARINC_1 --port-option
```

The first `Find` is a broadcast and should discover the board without being
told its address. `Information` should end with
`Final Status Code: Operation completed (0003)`.

**9 · Full acceptance.**

```bat
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target 192.168.0.3 -CliBuild <cli-build>
```

```c
-> arinc615aVerifyTestUpload "/sd0a/arinc_test"
```

### A complete CLI session with the board

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operator (PC)
    participant C as CLI Tool Suite
    participant B as Board · tArinc
    participant S as SD card

    Op->>C: -c Find
    C->>B: FIND IRQ · broadcast · UDP 1001
    B-->>C: IAN · ARINC · THA · ARINC_1
    Op->>C: -c Information --target-id=ARINC_1
    C->>B: read ARINC_1.LCI
    B->>C: LCL · 'ARINC 615A Test' · TEST001 · DEMO-PN
    Op->>C: -c AdhocUpload --load-header=DEMOLOAD.LUH
    C->>B: LUI · LUR
    B->>C: fetch DEMOLOAD.LUH · payload.bin
    B->>S: write /sd0a/arinc_test/upload/payload.bin
    B->>B: check length · CRC16
    B->>C: LUS · 0003 Completed
    Op->>C: -c OpDownload --file=payload.bin
    B->>S: read /sd0a/arinc_test/download/payload.bin
    B->>C: LNL · payload.bin · LNS 0003
```

### Within the system

There are two ways to run the target and the CLI together without a
separate test bench.

#### On one PC, with no board

The same target code builds as `arinc_host_runner`. Run it in WSL, and the
Windows CLI talks to it across the virtual network, exactly as it would to the
board. This is how the [CLI test run](#how-it-was-actually-tested-and-the-result)
was done.

```mermaid
flowchart LR
    subgraph WIN["Windows 11"]
        CLI2["arinc_615a_operation.exe<br/>+ cli_acceptance.ps1"]
    end
    subgraph WSL["WSL 2 Ubuntu · 172.x.x.x"]
        RUN["arinc_host_runner<br/><i>same THA code · VxWorks wake-up path</i>"]
        FS2["/tmp/arinc_cli<br/><i>upload · download</i>"]
        RUN --> FS2
    end
    CLI2 <-->|"vEthernet (WSL)<br/>FIND 11001 · TFTP 10059"| RUN

    classDef pc fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef brd fill:#238636,stroke:#116329,color:#fff
    class CLI2 pc
    class RUN,FS2 brd
```

Ports move to 11001 and 10059 because Linux reserves ports below 1024 for root.
The commands are in [Rehearse without a board](#rehearse-without-a-board).

#### Inside the UVDR system on the board

In service, the ARINC 615A target runs **next to the UVDR application** on the
same VxWorks image. It shares the network interface and the SD card, but has its
own task, ports and folders.

```mermaid
flowchart TB
    subgraph VX["VxWorks 24.03 kernel · LS1028A"]
        direction TB
        subgraph UVDR["UVDR application DKM"]
            REC["recording · Ch10 writer ·<br/>video · serial listener tasks"]
        end
        subgraph ARINC["ARINC 615A DKM"]
            TA["tArinc<br/><i>one task · event loop</i>"]
        end
        NET["IPNET · memac0 · 192.168.0.3"]
        SDC["SD card"]
        SCRIPT["startup script<br/><i>boot line s=…</i>"]
        SCRIPT -->|"ld · taskSpawn"| UVDR
        SCRIPT -->|"ld · arinc615aSelfTest · taskSpawn"| ARINC
        REC --> NET
        TA -->|"UDP 1001 · 59"| NET
        REC -->|"/sd0a · /sd0b · /sd0d · /sd1a"| SDC
        TA -->|"/sd0a/ARINC/upload · download"| SDC
    end
    NET <-->|Ethernet| DL["Data loader<br/>CLI Tool Suite"]

    classDef uv fill:#5A6472,stroke:#3D4551,color:#fff
    classDef ar fill:#238636,stroke:#116329,color:#fff
    classDef os fill:#0B5CA8,stroke:#083F73,color:#fff
    classDef dl fill:#1F6FEB,stroke:#0D419D,color:#fff
    class REC uv
    class TA ar
    class NET,SDC,SCRIPT os
    class DL dl
```

To start it automatically at boot, the image already includes
`INCLUDE_STARTUP_SCRIPT`. Put a shell script on the SD card and set the boot
line's startup-script field (`s=`) to it:

```c
/* /sd0a/startup.cmd, run by the kernel shell at boot */
ld < /sd0a/ARINC615A.out
arinc615aSelfTest
taskSpawn("tArinc", 150, 0x01000000, 0x100000, arinc615aRun, "/sd0a/ARINC/target-config.json")
```

Rules for sharing the board:

- **Priority.** Give `tArinc` a *lower* priority than the UVDR recording tasks
  (a higher number; `150` above, where `100` is used for testing). Data loading
  then never delays recording. Check the UVDR task priorities with `i`.
- **Storage.** Keep ARINC folders separate from UVDR data. Uploads go only to the
  configured upload directory, and path traversal is rejected, so a load can
  never overwrite `/sd0d/TMATS-Config.xml` or recordings.
- **Ports.** ARINC uses UDP 1001 and 59 only. Make sure no UVDR task binds them.
- **Config.** Use a production `target-config.json` with the real hardware ID, serial
  and part numbers (see `START_HERE.md` §5), not the `DEMO-PN` test config.

---

## Test procedure

Testing is layered. Each layer proves something the one before cannot, and the
last two are run against the board itself.

```mermaid
flowchart TB
    L1["<b>1 · Host regression</b><br/>229 cases · 1,706 assertions<br/><i>protocol logic, codecs, runtime</i>"]
    L2["<b>2 · VxWorks preflight</b><br/>129/129 files compiled with __VXWORKS__<br/><i>Asio config · m_data · include chain</i>"]
    L3["<b>3 · Image audit and dependency audit</b><br/><i>every external symbol vs the office VSB/VIP</i>"]
    L4["<b>4 · Protocol peer on the board</b><br/>vxworks_target_test.py · 9 checks<br/><i>independent implementation + negative tests</i>"]
    L5["<b>5 · Real data loader on the board</b><br/>cli_acceptance.ps1 · 7 checks<br/><i>ARINC 615A CLI Tool Suite</i>"]
    L1 --> L2 --> L3 --> L4 --> L5

    classDef host fill:#1F6FEB,stroke:#0D419D,color:#fff
    classDef board fill:#238636,stroke:#116329,color:#fff
    class L1,L2,L3 host
    class L4,L5 board
```

### Layer 1 — Host build and offline verification

Any Linux or WSL machine with a C++17 compiler, CMake 3.24+, Ninja and Python 3.
Nothing is downloaded: Boost is unpacked from the bundled archive and checked
against its SHA-256.

```bash
cmake -S . -B build -G Ninja -DARINC_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

```text
1/3 Test #2: arinc_self_test ..................   Passed
2/3 Test #1: arinc_regression .................   Passed
3/3 Test #3: arinc_network_transfers ..........   Passed
100% tests passed, 0 tests failed out of 3
```

`arinc_regression` runs 229 test cases with 1,706 assertions (see
`build/Testing/Temporary/LastTest.log`).

### Layer 2 — VxWorks preflight

Compiles every production file with `__VXWORKS__` and `_WRS_KERNEL` defined,
against stub SDK headers. The stub `sockLib.h` defines the real `m_data` macro, so
a missing fix fails here, not in the office.

```bash
cmake --build build --target arinc_vxworks_preflight
```

```text
VxWorks-branch syntax check: 129/129 clean
Boost platform profile: VxWorks 7
Boost.Asio reactor:     select
Asio local sockets:     disabled
Asio interrupter:       socket
Asio include chain, VxWorks (__VXWORKS__)  -> selectLib_h
VxWorks preflight passed.
```

### Layer 3 — Dependency audit

```bash
cmake --build build --target arinc_target_audit
```

Checks that no excluded library (Qt, Helper, program_options, ARINC 649 and so
on) leaks into the target archives, and records every header dependency.

### Layer 4 — Protocol peer against the board

[`tests/vxworks_target_test.py`](tests/vxworks_target_test.py) is an independent
UDP/TFTP peer written against the standard, not against this code. It uses only
the Python standard library. With `tArinc` running (see [Runtime](#runtime--load-and-run-on-the-board)):

```bat
ping 192.168.0.3
python tests\vxworks_target_test.py --target 192.168.0.3
```

| ID | Check |
| --- | --- |
| T01 | FIND answered with hardware ID `ARINC` |
| T02 | Information: `LCL` has `DEMO-PN`/`TEST001`; one DATA packet is **dropped on purpose** and must be retransmitted |
| T03 | Operator Defined Download: listing, selection, 4097-byte payload byte-identical |
| T04 | Media Defined Download: payload byte-identical, completed status |
| T05 | Upload: ARINC 665 header + payload, completed |
| T06 | Malformed FIND ignored; the next FIND is answered |
| T07 | Empty, malformed and **path-traversal** load headers rejected (`0x1003`); target keeps serving |
| T08 | Corrupt and truncated payloads rejected; the next valid upload succeeds |
| T09 | `--soak N`: N upload + download cycles, for memory checks with `memShow` |

```text
PASS: T01 FIND answered by 192.168.0.3
PASS: T02 Information: LCL has DEMO-PN/TEST001 (one lost DATA packet retransmitted)
…
ALL 9 CHECKS PASSED in 7.5 s. Now run on the target: arinc615aVerifyTestUpload "<root>"
```

Then, on the board:

```c
-> arinc615aVerifyTestUpload "/sd0a/arinc_test"
ARINC upload check PASS (payload byte-identical, no path-traversal file)
```

Options: `--find-port`, `--tftp-port`, `--target-id`, `--thw-id`, `--serial`,
`--timeout`, `--soak N`, `--bind <PC-IP>`.

### Layer 5 — Data loader CLI acceptance

The decisive test: the **real data loader**, `arinc_615a_operation.exe` from the
[ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite),
against the target. [`tests/cli_acceptance.ps1`](tests/cli_acceptance.ps1) runs
every operation and builds an ARINC 665 media set for the upload.

```mermaid
sequenceDiagram
    autonumber
    participant S as cli_acceptance.ps1
    participant C as arinc_615a_operation.exe
    participant T as Target (tArinc)

    S->>C: -c Find
    C->>T: FIND IRQ · UDP 1001
    T-->>C: IAN · ARINC_1
    S->>C: -c Information
    C->>T: LCI → accepted
    T->>C: LCL · hardware + DEMO-PN
    S->>C: -c OpDownload · -c MedDownload
    T->>C: LNL list · payload.bin · LNS completed
    Note over S: payload.bin compared byte for byte
    S->>S: arinc_665_media_set_compiler → DEMO-MS
    S->>C: -c AdhocUpload DEMOLOAD.LUH
    C->>T: LUI · LUR
    T->>C: fetch DEMOLOAD.LUH + payload.bin
    T-->>C: LUS completed (CRC checked)
    S->>C: -c Find (still alive?)
```

#### One-time CLI setup

> [!WARNING]
> **Apply the exit-hang patch first.** In the published CLI suite, the command
> registry is declared before the `io_context`, so it is destroyed after it. That
> is undefined behaviour. A clean A/B test on the MSVC **debug** build (same build
> tree, a fresh target for every run, the operation confirmed complete on the wire
> each time) gave: **unpatched, 5 of 5 runs hung at exit** with no result printed;
> **patched, 0 of 5 hung** and all 5 printed `Operation completed`. The unpatched
> **release** build exited normally in 5 of 5 runs, but the destruction order is
> still wrong. The one-line reorder is in
> [`tests/cli/arinc_615a_operation-exit-hang.patch`](tests/cli/arinc_615a_operation-exit-hang.patch).

```bat
cd <cli-suite>
git apply <this-repo>\tests\cli\arinc_615a_operation-exit-hang.patch
build.bat --no-run
cmake --build <cli-build> --target arinc_665_media_set_compiler
```

Let the CLI receive UDP from the board. Run this once, in an elevated `cmd`:

```bat
netsh advfirewall firewall add rule name="ARINC615A loader CLI (UDP in)" dir=in action=allow protocol=UDP profile=private program="<cli-build>\app\arinc_615a_operation\arinc_615a_operation.exe"
```

#### Run

```bat
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target 192.168.0.3 -CliBuild <cli-build>
```

Expected output:

```text
PASS: C01 FIND answered by 192.168.0.3 with target ID ARINC_1
PASS: C02 Information: integrity valid, part number DEMO-PN, completed
PASS: C03 Operator Defined Download: file list received, payload.bin byte-identical, completed
PASS: C04 Media Defined Download: payload.bin byte-identical, completed
PASS: C05 ARINC 665 media set DEMO-MS compiled
PASS: C06 Adhoc Upload of DEMOLOAD.LUH (DEMO-PN): load and operation completed
PASS: C07 Target still answers FIND after all operations

7 passed, 0 failed.
```

Finish with `arinc615aVerifyTestUpload "/sd0a/arinc_test"` on the board.

#### How it was actually tested, and the result

The target has been run against the CLI Tool Suite's `arinc_615a_operation.exe`,
but **not yet on the board**. The target application ran on the same PC in WSL:

| | Used in the test run |
| --- | --- |
| Data loader | `arinc_615a_operation.exe`, MSVC 2022 debug build from the local ARINC-EXAMPLE tree. This is the same `arinc_615a_operation` source the [CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite) publishes (the patch applies unchanged to both), **with the exit-hang patch** applied |
| Target | `arinc_host_runner` from the freshly unzipped handoff, built with the VxWorks wake-up path (`-DARINC_ASIO_SOCKET_SELECT_INTERRUPTER=1`), running the same `arinc615aPrepareTest` + `arinc615aRun` code as the DKM |
| Network | Windows 11 → WSL 2 Ubuntu, target at `172.20.60.83`, FIND port `11001`, TFTP port `10059` (Linux needs root for ports below 1024) |
| Firewall | Rule letting the CLI receive UDP from the WSL range |

The steps, exactly as run:

```bash
# 1. WSL: start the target
./build_sock/arinc_host_runner --prepare /tmp/arinc_cli
sed -i 's/"port": 59,/"port": 10059,/; s/"find_port": 1001/"find_port": 11001/' /tmp/arinc_cli/test-config.json
./build_sock/arinc_host_runner /tmp/arinc_cli/test-config.json
```

```bat
REM 2. Windows: run the loader against it
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target 172.20.60.83 -CliBuild <cli-build> -FindPort 11001 -TftpPort 10059
```

```bash
# 3. WSL: check what the target stored
./build_sock/arinc_host_runner --verify /tmp/arinc_cli
```

The result:

```text
PASS: C01 FIND answered by 172.20.60.83 with target ID ARINC_1
PASS: C02 Information: integrity valid, part number DEMO-PN, completed
PASS: C03 Operator Defined Download: file list received, payload.bin byte-identical, completed
PASS: C04 Media Defined Download: payload.bin byte-identical, completed
PASS: C05 ARINC 665 media set DEMO-MS compiled
PASS: C06 Adhoc Upload of DEMOLOAD.LUH (DEMO-PN): load and operation completed
PASS: C07 Target still answers FIND after all operations

7 passed, 0 failed.

ARINC upload check PASS (payload byte-identical, no path-traversal file)
```

What the CLI reported for each operation (abridged):

```text
-c Find          Response from 172.20.60.83: THW ID 'ARINC' · THW Type Name 'THA' · ** Target ID ** 'ARINC_1'
-c Information   Initialisation Code: Operation Accepted (0001) · Information Integrity: Valid
                 Literal Name 'ARINC 615A Test' · Serial Number 'TEST001' · Part Number 'DEMO-PN'
                 Final Status Code: Operation completed (0003)
-c OpDownload    Received File List: demo.LUH 104 · empty.LUH 62 · payload.bin 4097 · traversal.LUH 106
                 payload.bin 0003 · demo.LUH 0003 · Final Status Code: Operation completed (0003)
-c MedDownload   payload.bin: Transfer OK · 4097 bytes · Final Status Code: Operation completed (0003)
-c AdhocUpload   DEMOLOAD.LUH · Part Number 'DEMO-PN' · Ratio 100% · Final Status Code: Operation completed (0003)
```

The same run with the unpatched CLI finished every operation on the wire, then
hung at exit without printing a result. That is how the exit-hang bug was found.

#### Running the CLI by hand

```bat
set PATH=C:\vi\x64-windows\bin;%PATH%      REM suite scripts; for a debug build use C:\vi\x64-windows\debug\bin
arinc_615a_operation.exe -c Find        --target-address=192.168.0.3
arinc_615a_operation.exe -c Information --target-address=192.168.0.3 --target-id=ARINC_1 --port-option
arinc_615a_operation.exe -c OpDownload  --target-address=192.168.0.3 --target-id=ARINC_1 --port-option --file=payload.bin
```

> [!TIP]
> Always use `--option=value`. Several short options clash (`-l`, `-t`), and
> `--target-address` followed by a space swallows the next argument. A missing
> DLL shows up as exit code `0xC0000135`; put the vcpkg `bin` folder on `PATH`.
> `cli_acceptance.ps1` does this itself. It finds `C:\vi` or `<cli-build>\vcpkg_installed`
> and picks debug or release DLLs from the exe's imports; override with `-VcpkgInstalled`.

### Lifecycle and resource checks

```c
-> arinc615aStop                  /* then restart 3 times; each cycle must pass layer 4 */
-> taskSpawn("tArinc2", …)        /* a second runtime must be rejected */
-> checkStack "tArinc"            /* high-water mark well below 1 MiB, no OVERFLOW */
-> memShow                        /* before and after --soak 50: no downward trend */
```

Every step, with expected results and a results sheet to fill in, is in
[`workbench/VXWORKS_TEST_PROCEDURE.md`](workbench/VXWORKS_TEST_PROCEDURE.md).
Call the port board-validated only when all of its rows pass.

---

## Rehearse without a board

The same entry points build into a host program, `arinc_host_runner`, so the
whole procedure can run on a PC (Linux or WSL) before any board time. Ports
below 1024 need root on Linux, so the rehearsal moves them:

```bash
./build/arinc_host_runner --prepare /tmp/arinc
sed -i 's/"port": 59,/"port": 10059,/; s/"find_port": 1001/"find_port": 11001/' /tmp/arinc/test-config.json
./build/arinc_host_runner /tmp/arinc/test-config.json        # Enter stops it
```

From Windows, against the WSL IP (`wsl hostname -I`):

```bat
python tests\vxworks_target_test.py --target <wsl-ip> --find-port 11001 --tftp-port 10059 --soak 20
powershell -ExecutionPolicy Bypass -File tests\cli_acceptance.ps1 -Target <wsl-ip> -CliBuild <cli-build> -FindPort 11001 -TftpPort 10059
```

To test the **VxWorks code path** on the host, add
`-DCMAKE_CXX_FLAGS=-DARINC_ASIO_SOCKET_SELECT_INTERRUPTER=1` to the CMake configure.

> A rehearsal pass proves the procedure and the protocol, not VxWorks. The board
> run is still required.

---

## Test results

Latest run: 25–26 September 2026, on `main`.

| Layer | Environment | Result |
| --- | --- | --- |
| Host regression | WSL Ubuntu · GCC 15.2 · CMake 4.2 | ✅ 229/229 cases · 1,706 assertions |
| Package self-test + network suite | Fresh unzip of the handoff, normal and VxWorks-path builds | ✅ 2/2 · 2/2 |
| VxWorks preflight | `__VXWORKS__` + stub SDK | ✅ 129/129 · socket interrupter · `selectLib.h` |
| Dependency audit | `arinc_target_audit` | ✅ passed |
| Unresolvable-on-image symbols | VxWorks-path build vs office image | ✅ none (`pipe`, `eventfd`, `socketpair`, `pthread_rwlock` all gone) |
| Protocol peer | Windows Python → target in WSL | ✅ 9/9 including 20-cycle soak |
| **Real data loader** | **ARINC 615A CLI Tool Suite (MSVC) → target in WSL** | ✅ **7/7** · upload verified on target |
| CLI exit-hang patch, A/B | MSVC debug CLI, fresh target per run | ✅ unpatched 5/5 hung · patched 0/5 hung, 5/5 results |
| One-line install | Bare Ubuntu 24.04/22.04, Debian 12, Fedora 41, Arch, openSUSE · WSL · Windows | ✅ all passed, cloned from GitHub |
| Workbench DKM build | Office SDK | ⏳ pending, in the office |
| Board run (layers 4 and 5) | LS1028A board | ⏳ pending, in the office |

---

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Select a VxWorks Downloadable Kernel Module project` | The project is an RTP. Recreate it as a DKM |
| `sys/poll.h` not found | The bundled Asio overlay was overwritten. Restore `include/boost/asio/detail/` from the package |
| Unresolved `pipe` at `ld` | The interrupter patch is missing: check `BuildConfig.hpp` and `select_interrupter.hpp` (or add `INCLUDE_POSIX_PIPES` to the image) |
| `<filesystem>` not found | The VSB lacks C++17 filesystem support; this is a platform configuration item |
| FIND times out | Wrong IP or subnet (`ping` first), PC firewall, `tArinc` not running (`i`), or UDP 1001 already in use |
| FIND works, transfers time out | The PC firewall is dropping the board's TFTP transfers back to the loader. Add the firewall rule, or use `--bind <PC-IP>` on a multi-homed PC |
| Valid upload rejected with `0x1003` | The upload folder is not writable. Check `devs`, `ls "/sd0a/arinc_test/upload"` and free space |
| `tArinc` is `SUSPEND` | It crashed. Check `checkStack` and `tt tArinc`; raise the stack to `0x200000` and keep `VX_FP_TASK` |
| CLI never exits | Apply `tests/cli/arinc_615a_operation-exit-hang.patch` to the CLI suite |
| CLI exits with `0xC0000135` | vcpkg DLLs are not on `PATH` |

---

## Repository layout

```
.
├── workbench/                     Workbench-facing sources and docs
│   ├── EntryPoints.cpp/.h         arinc615aSelfTest · Demo · Run · Stop
│   ├── TestSupport.cpp            arinc615aPrepareTest · VerifyTestUpload · WriteFixtures
│   ├── START_HERE.md              office build guide
│   ├── VXWORKS_TEST_PROCEDURE.md  board acceptance procedure + results sheet
│   ├── BUILD_OPTIONS.txt          compiler flags and include paths for the DKM
│   └── target-config.json         sample runtime configuration
├── lib/
│   ├── arinc_615a/                protocol library (target, find, files, tftp options)
│   ├── tftp/                      TFTP client/server
│   ├── arinc_checksum/            CRC and hash check values
│   └── arinc_support/             BuildConfig.hpp · BoostVxWorks.hpp · utilities
├── app/arinc_615a_unit_test/arinc_615a_test_tha/   THA application (JSON → operations)
├── third_party/
│   ├── arinc_665/                 ARINC 665 load format (bundled)
│   ├── boost_1_88_0_headers.tar.gz   Boost, SHA-256 verified, unpacked offline
│   └── boost_vxworks_overlay/     VxWorks fixes to Boost.Asio (poll · socketpair · m_data)
├── tests/
│   ├── vxworks_target_test.py     layer 4 · protocol peer · 9 checks
│   ├── cli_acceptance.ps1         layer 5 · data loader CLI · 7 checks
│   ├── cli/                       exit-hang patch for the CLI suite
│   ├── vxworks_preflight/         layer 2 · VxWorks-branch compile check
│   └── network_smoke.py …         layer 1 · host suites
├── tools/prepare_office.py        builds the Workbench handoff package
├── delivery/ARINC615A_OFFICE_READY.zip   ready-to-build handoff for the office
├── VALIDATION.md                  what has been proven, and how
└── docs/UPSTREAM_README.md        original upstream README (desktop suite)
```

### Regenerating the handoff

```bash
mkdir -p /tmp/src && git -c core.autocrlf=false archive HEAD | tar -x -C /tmp/src && cd /tmp/src
cmake -S . -B build -G Ninja -DARINC_BUILD_TESTS=ON && cmake --build build
python3 tools/prepare_office.py --build build --source-commit "$(git -C <repo> rev-parse HEAD)" \
  --output /tmp/pkg/ARINC615A_OFFICE_READY
```

The generator refuses to overwrite, writes `SHA256SUMS.txt` and `BUILD_INFO.txt`,
and zips the result. Use the `archive` step with `core.autocrlf=false`, or Windows
line endings leak into every file.

---

## Documentation

| Document | What's in it |
| --- | --- |
| **[workbench/START_HERE.md](workbench/START_HERE.md)** | **Start here in the office.** Workbench project setup, build options, first-build troubleshooting, runtime and acceptance checklist |
| **[workbench/VXWORKS_TEST_PROCEDURE.md](workbench/VXWORKS_TEST_PROCEDURE.md)** | Phases A–I on the board, with exact commands, expected output, troubleshooting and a results sheet |
| **[VALIDATION.md](VALIDATION.md)** | What has been verified, on what, and what is still open |
| **[tests/vxworks_preflight/README.md](tests/vxworks_preflight/README.md)** | What the VxWorks preflight checks and why |
| **[third_party/DEPENDENCIES.md](third_party/DEPENDENCIES.md)** | Bundled dependencies and their licences |
| **[VxWorksDKM.md](VxWorksDKM.md)** | Alternative static-library cross-build |
| **[docs/UPSTREAM_README.md](docs/UPSTREAM_README.md)** | The original upstream README for the desktop suite |

**Related:** [ARINC 615A CLI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-cli-tool-suite)
(the data loader used to test this target) ·
[ARINC 615A GUI Tool Suite](https://github.com/Hitheshkaranth/arinc-615a-gui-tool-suite)

---

## Protocol background

The library implements **ARINC 615A Supplements 2, 3 and 4**. The target
announces its protocol version, and the loader adapts to it.

| Supplement | Notable changes |
| --- | --- |
| **615A-1** | Uppercase protocol filenames · UDP port 59 · block-size option mandatory for the host · exception timer in status files |
| **615A-2** | SNIP renamed **FIND** and made optional · protocol version `A3` · `LCL` gains multiple target hardware and part-number amendments |
| **615A-3** | Transfer-size and timeout options optional · **checksum** and **port** options · status `0004` |
| **615A-4** | Part-number option corrected · checksum option description updated |

**References:** ARINC 615A-4 (Software Data Loader Using Ethernet Interface) ·
ARINC 665-5 (Loadable Software Standards) · ARINC 645-1 (Common Terminology and
Functions for Software Distribution and Loading).

---

## Licence

[![Licence](https://img.shields.io/badge/Licence-MPL--2.0-A6CE39?style=flat-square&logo=mozilla&logoColor=white)](LICENSE)

Mozilla Public License 2.0. Based on the ARINC 615A Tool Suite © Thomas Vogt,
<https://git.thomas-vogt.de/thomas-vogt/arinc_615a>. The MPL requires this licence
and its attribution to be kept in redistributions. Bundled Boost is under the
Boost Software License 1.0; see [`third_party_licenses/`](third_party_licenses).

ARINC® is a trademark of its respective owner. This project implements the
publicly documented ARINC 615A protocol and is **not affiliated with, endorsed
by, or a product of ARINC**. The ARINC standards themselves are not
redistributed here.

VxWorks® and Wind River® are trademarks of Wind River Systems, Inc. The VxWorks
wordmark in the banner is a plain typographic rendering that only identifies the
target platform. This project is not affiliated with or endorsed by Wind River,
and contains no Wind River SDK code.
