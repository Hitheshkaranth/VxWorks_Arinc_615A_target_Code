#!/usr/bin/env bash
# One-command setup and usage for the ARINC 615A VxWorks target on Linux / WSL.
#
#   ./setup.sh                  install missing tools, build, run every host check
#   ./setup.sh rehearse         start a local target, drive it with the protocol peer, stop
#   ./setup.sh run              run the target on this machine until Enter is pressed
#   ./setup.sh test <ip> [..]   test a running target (the VxWorks board) from this machine
#   ./setup.sh help
#
# Environment: ARINC_BUILD_DIR (default ./build), ARINC_TFTP_PORT and ARINC_FIND_PORT
# for `run` (defaults 59/1001 as root, otherwise 10059/11001).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="${ARINC_BUILD_DIR:-$ROOT/build}"
TOOLCHAIN="$ROOT/.toolchain"
CMAKE_MIN="3.24"
CMAKE_FETCH="3.31.6"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32mPASS\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mFAIL\033[0m %s\n' "$*" >&2; exit 1; }
as_root() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

install_deps() {
  local missing=()
  command -v g++ >/dev/null     || missing+=(g++)
  command -v ninja >/dev/null   || missing+=(ninja)
  command -v python3 >/dev/null || missing+=(python3)
  command -v cmake >/dev/null   || missing+=(cmake)
  if [ ${#missing[@]} -gt 0 ]; then
    say "Installing missing tools: ${missing[*]}"
    if command -v apt-get >/dev/null; then
      as_root apt-get update -qq
      as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq g++ ninja-build python3 cmake curl ca-certificates >/dev/null
    elif command -v dnf >/dev/null; then
      as_root dnf install -y -q gcc-c++ ninja-build python3 cmake curl
    elif command -v pacman >/dev/null; then
      as_root pacman -Sy --noconfirm --needed gcc ninja python cmake curl
    elif command -v zypper >/dev/null; then
      as_root zypper --non-interactive install gcc-c++ ninja python3 cmake curl
    else
      die "No supported package manager. Install g++ (C++17), ninja, python3 and cmake >= $CMAKE_MIN."
    fi
  fi

  # Older distributions (e.g. Ubuntu 22.04: CMake 3.22) are below the minimum:
  # fetch the official Kitware binary into a git-ignored .toolchain/.
  local have
  have="$(cmake --version 2>/dev/null | head -1 | awk '{print $3}')"
  if [ -x "$TOOLCHAIN/bin/cmake" ]; then
    export PATH="$TOOLCHAIN/bin:$PATH"
  elif ! version_ge "${have:-0}" "$CMAKE_MIN"; then
    say "CMake ${have:-none} < $CMAKE_MIN: fetching CMake $CMAKE_FETCH into .toolchain/"
    command -v curl >/dev/null || die "curl is needed to fetch CMake"
    local arch; arch="$(uname -m)"; [ "$arch" = "arm64" ] && arch=aarch64
    mkdir -p "$TOOLCHAIN"
    curl -fsSL "https://github.com/Kitware/CMake/releases/download/v$CMAKE_FETCH/cmake-$CMAKE_FETCH-linux-$arch.tar.gz" \
      | tar -xz -C "$TOOLCHAIN" --strip-components=1
    export PATH="$TOOLCHAIN/bin:$PATH"
  fi
  ok "tools: $(g++ -dumpfullversion) · cmake $(cmake --version | head -1 | awk '{print $3}') · ninja $(ninja --version) · $(python3 --version)"
}

build() {
  install_deps
  say "Configuring (offline: Boost is unpacked from third_party/, SHA-256 checked)"
  cmake -S "$ROOT" -B "$BUILD" -G Ninja -DARINC_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug >/dev/null
  say "Building"
  cmake --build "$BUILD" -j"$(nproc)" >/dev/null || cmake --build "$BUILD" -j1
  ok "build"
}

checks() {
  say "Host regression, self-test and network suite"
  ctest --test-dir "$BUILD" -j4 --output-on-failure | tail -3
  ok "$(grep -hE 'test cases|assertions' "$BUILD/Testing/Temporary/LastTest.log" | sed 's/^ *//' | tr '\n' ' ')"
  say "VxWorks preflight"
  cmake --build "$BUILD" --target arinc_vxworks_preflight | grep -E 'syntax check|interrupter|preflight passed'
  say "Dependency audit"
  cmake --build "$BUILD" --target arinc_target_audit | grep -E 'audit passed'
  ok "all host checks passed · next: ./setup.sh rehearse"
}

runner() { echo "$BUILD/arinc_host_runner"; }

ports() {
  if [ "$(id -u)" -eq 0 ]; then TFTP="${ARINC_TFTP_PORT:-59}"; FIND="${ARINC_FIND_PORT:-1001}"
  else TFTP="${ARINC_TFTP_PORT:-10059}"; FIND="${ARINC_FIND_PORT:-11001}"; fi
}

prepare_root() {
  local root="$1"
  [ -x "$(runner)" ] || build
  "$(runner)" --prepare "$root" >/dev/null
  sed -i "s/\"port\": 59,/\"port\": $TFTP,/; s/\"find_port\": 1001/\"find_port\": $FIND/" "$root/test-config.json"
}

run_target() {
  ports
  local root="${ARINC_ROOT:-/tmp/arinc615a-target}"
  prepare_root "$root"
  local ip; ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  say "Target ARINC_1 on ${ip:-this host}: FIND UDP $FIND · TFTP UDP $TFTP · files in $root"
  echo "    Linux : ./setup.sh test ${ip:-127.0.0.1} --find-port $FIND --tftp-port $TFTP"
  echo "    CLI   : setup.bat cli ${ip:-<ip>} <cli-build> -FindPort $FIND -TftpPort $TFTP"
  echo "    Press Enter to stop."
  "$(runner)" "$root/test-config.json"
  "$(runner)" --verify "$root" || true
}

rehearse() {
  ports
  [ -x "$(runner)" ] || build
  local root; root="$(mktemp -d /tmp/arinc615a-rehearse.XXXX)"
  prepare_root "$root"
  say "Rehearsal: target on 127.0.0.1 (FIND $FIND, TFTP $TFTP), protocol peer with 20 soak cycles"
  local fifo="$root/stop"; mkfifo "$fifo"
  "$(runner)" "$root/test-config.json" < "$fifo" > "$root/target.log" 2>&1 &
  local pid=$!
  exec 3>"$fifo"
  sleep 0.5
  local rc=0
  python3 "$ROOT/tests/vxworks_target_test.py" --target 127.0.0.1 --find-port "$FIND" --tftp-port "$TFTP" --soak 20 || rc=$?
  "$(runner)" --verify "$root" || rc=1
  echo stop >&3; exec 3>&-
  wait "$pid" || rc=1
  [ "$rc" -eq 0 ] && ok "rehearsal: protocol peer, upload verify and clean stop" || die "rehearsal failed, see $root/target.log"
}

test_target() {
  [ $# -ge 1 ] || die "usage: ./setup.sh test <target-ip> [vxworks_target_test.py options]"
  local ip="$1"; shift
  command -v python3 >/dev/null || install_deps
  python3 "$ROOT/tests/vxworks_target_test.py" --target "$ip" "$@"
}

case "${1:-setup}" in
  setup|install) build; checks ;;
  build)         build ;;
  check)         checks ;;
  run)           run_target ;;
  rehearse)      rehearse ;;
  test)          shift; test_target "$@" ;;
  help|-h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "unknown command '$1' (try ./setup.sh help)" ;;
esac
