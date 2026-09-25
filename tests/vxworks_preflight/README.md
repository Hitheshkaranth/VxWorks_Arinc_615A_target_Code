# VxWorks preflight check

```sh
cmake --build <build> --target arinc_vxworks_preflight
```

## Why this exists

`lib/arinc_support/BuildConfig.hpp` and `lib/arinc_support/BoostVxWorks.hpp`
contain a block that is compiled only when `__VXWORKS__` is defined. No host
compiler defines it, so an ordinary host build leaves that code — the kernel
includes, the `_WRS_KERNEL` guard, the Boost platform profile and the Asio
backend selection — completely uncompiled. It would first meet a compiler in
the office, on the licensed SDK, which is the worst place to discover a typo.

This target compiles all production translation units with `__VXWORKS__` and
`_WRS_KERNEL` defined, against the stub headers in `sdk_stub/`.

## What it checks

- Every production translation unit is syntactically valid with the VxWorks
  branch active, with no warnings under `-Wall`.
- Boost selects the `VxWorks 7` platform profile from `BoostVxWorks.hpp`.
- Boost.Asio selects the `select` reactor, not kqueue, epoll or `/dev/poll`.
- Asio local (Unix-domain) sockets are disabled.
- The stub `sockLib.h` defines the `mbuf.h` `m_data` macro, so a leak into
  Boost.PropertyTree fails the syntax check.
- Asio wakes the select reactor through its loopback-socket interrupter, not
  `pipe()`, which needs `INCLUDE_POSIX_PIPES` (absent from the office image).
- The bundled Asio patch, read from the real `socket_types.hpp`, routes a
  VxWorks cross-compiler to `<selectLib.h>` under both macro spellings, while
  leaving Linux, macOS and other POSIX hosts on their existing header.

The last check is evaluated against the live header rather than a copy, so
losing the patch during a Boost refresh fails the target.

## What it does NOT prove

The stub headers in `sdk_stub/` are **not** Wind River headers. They are a
minimal approximation, backed by the host libc, written only to let the
`__VXWORKS__` branch reach a compiler. Passing this check does **not** mean
the Workbench build will succeed. In particular it says nothing about:

- whether the real VxWorks 24.03 headers match these stubs,
- whether the 24.03 libc++ provides working kernel-mode `std::filesystem`,
  exceptions and RTTI (`std::filesystem` is load-bearing for upload/download),
- linking, DKM load or unresolved symbols, which survive a clean compile,
- any runtime or on-target behaviour.

The licensed VxWorks 24.03 SDK, VSB/BSP and board remain the acceptance gate.
See `VALIDATION.md` and `workbench/START_HERE.md`.
