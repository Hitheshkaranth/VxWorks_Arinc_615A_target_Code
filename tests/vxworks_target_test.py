#!/usr/bin/env python3
"""Acceptance test for the ARINC 615A target running on a real VxWorks board.

Run from the Windows (or any) PC on the same subnet as the board, after the
board has executed, in its kernel shell:

    arinc615aPrepareTest "/sd0a/arinc_test"
    taskSpawn "tArinc",100,0x01000000,0x100000,arinc615aRun,"/sd0a/arinc_test/test-config.json"

The board creates its own fixtures, so no file copy is needed. This script
downloads the fixtures from the board, checks them against the reference
pattern, then serves them back for the upload tests. Afterwards, run
`arinc615aVerifyTestUpload "/sd0a/arinc_test"` on the board.

Python standard library only. See VXWORKS_TEST_PROCEDURE.md.
"""
import argparse
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import network_smoke as net  # noqa: E402
from network_smoke import Peer, protocol, read_file, string, write_file  # noqa: E402

ACCEPTED = b'\0\1'
COMPLETED = b'\0\3'
REJECTED = b'\x10\x03'


def expected_payload():
    # Must match testPayload() in src/workbench/TestSupport.cpp.
    return bytes(i % 251 for i in range(4097))


class Board:
    def __init__(self, args, peer):
        self.args = args
        self.peer = peer
        self.remote = (args.target, args.tftp_port)
        self.passed = 0

    def ok(self, message):
        self.passed += 1
        print('PASS: ' + message, flush=True)

    def find(self, payload=b'\0\1\0\x10'):
        with net.udp() as probe:
            probe.settimeout(1)
            for _ in range(self.args.timeout):
                probe.sendto(payload, (self.args.target, self.args.find_port))
                try:
                    data, _ = probe.recvfrom(2048)
                    return data
                except socket.timeout:
                    continue
        raise AssertionError('FIND got no answer from %s:%d (IP, subnet, firewall, loader task running?)'
                             % (self.args.target, self.args.find_port))

    def begin(self, extension, drop_first=False):
        self.peer.received.clear()
        initial = read_file(self.remote, '%s.%s' % (self.args.target_id, extension),
                            {'port': self.peer.port}, drop_first)
        assert len(initial) >= 8 and initial[6:8] == ACCEPTED, \
            '%s not accepted: %r' % (extension, initial[:16])

    def wait_status(self, extension, code):
        return self.peer.wait(lambda n, d: n.endswith('.' + extension) and d[6:8] == code)

    def operator_download(self, name):
        self.begin('LNO')
        listing = self.peer.wait(lambda n, d: n.endswith('.LNL'))
        assert name.encode() in listing, '%s missing from LNL listing' % name
        write_file(self.remote, self.args.target_id + '.LNA', protocol(b'\0\1' + string(name)))
        data = self.peer.wait(lambda n, d: n == name)
        self.wait_status('LNS', COMPLETED)
        time.sleep(0.1)
        return data

    def media_download(self, name):
        self.begin('LND')
        self.peer.wait(lambda n, d: n.endswith('.LNS'))
        write_file(self.remote, self.args.target_id + '.LNR', protocol(b'\0\1' + string(name) + b'\0'))
        data = self.peer.wait(lambda n, d: n == name)
        self.wait_status('LNS', COMPLETED)
        time.sleep(0.1)
        return data

    def upload(self, header, expect):
        self.begin('LUI')
        self.wait_status('LUS', ACCEPTED)
        write_file(self.remote, self.args.target_id + '.LUR',
                   protocol(b'\0\1' + string(header) + string('DEMO-PN')))
        self.wait_status('LUS', expect)
        time.sleep(0.1)


def run(args):
    net.BIND_ADDRESS = args.bind
    net.SOCKET_TIMEOUT = args.timeout
    reference = expected_payload()
    peer = Peer({})
    board = Board(args, peer)
    started = time.monotonic()
    try:
        answer = board.find()
        assert args.thw_id.encode() in answer, 'FIND answer lacks thwId %r: %r' % (args.thw_id, answer)
        board.ok('T01 FIND answered by %s' % args.target)

        board.begin('LCI', drop_first=True)
        information = peer.wait(lambda n, d: n.endswith('.LCL'))
        assert b'DEMO-PN' in information, 'part number DEMO-PN missing from LCL'
        assert args.serial.encode() in information, 'serial %s missing from LCL' % args.serial
        board.ok('T02 Information: LCL has DEMO-PN/%s (one lost DATA packet retransmitted)' % args.serial)
        time.sleep(0.1)

        files = {}
        for name in ('payload.bin', 'demo.LUH', 'empty.LUH', 'traversal.LUH'):
            files[name] = board.operator_download(name)
        assert files['payload.bin'] == reference, 'downloaded payload.bin differs from the reference pattern'
        board.ok('T03 Operator Defined Download: listing, selection, 4097-byte payload byte-identical')

        assert board.media_download('payload.bin') == reference
        board.ok('T04 Media Defined Download: payload byte-identical, completed status')

        peer.files.update(files)
        board.upload('demo.LUH', COMPLETED)
        board.ok('T05 Upload: ARINC 665 header + payload completed (verify on target with arinc615aVerifyTestUpload)')

        with net.udp() as probe:
            probe.sendto(b'\0', (args.target, args.find_port))
        assert args.thw_id.encode() in board.find()
        board.ok('T06 Malformed FIND ignored; next valid FIND answered')

        peer.files['bad.LUH'] = b'bad'
        for header in ('empty.LUH', 'bad.LUH', 'traversal.LUH'):
            board.upload(header, REJECTED)
        board.ok('T07 Empty, malformed and path-traversal load headers rejected; target still serving')

        for corrupt in (b'X' + reference[1:], reference[:-1]):
            peer.files['payload.bin'] = corrupt
            board.upload('demo.LUH', REJECTED)
        peer.files['payload.bin'] = reference
        board.upload('demo.LUH', COMPLETED)
        board.ok('T08 Corrupt and truncated payloads rejected; following valid upload completed')

        for cycle in range(1, args.soak + 1):
            board.upload('demo.LUH', COMPLETED)
            assert board.media_download('payload.bin') == reference
            if cycle % 10 == 0 or cycle == args.soak:
                print('  soak %d/%d cycles OK' % (cycle, args.soak), flush=True)
        if args.soak:
            board.ok('T09 Soak: %d upload + download cycles' % args.soak)
    except socket.timeout:
        print('FAIL: no TFTP reply after step %d. If FIND passed, the PC firewall is most likely '
              'dropping the board\'s transfers to Python (allow python.exe inbound UDP, Private '
              'profile) or --bind names the wrong adapter.' % board.passed, flush=True)
        return 1
    except (AssertionError, OSError) as error:
        print('FAIL: %s' % error, flush=True)
        print('Check the target console for messages. %d checks passed before the failure.' % board.passed)
        return 1
    finally:
        try:
            peer.close()
        except AssertionError as error:
            print('FAIL: peer shutdown: %s' % error)
    print('ALL %d CHECKS PASSED in %.1f s. Now run on the target: arinc615aVerifyTestUpload "<root>"'
          % (board.passed, time.monotonic() - started))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', required=True, help='board IPv4 address')
    parser.add_argument('--find-port', type=int, default=1001)
    parser.add_argument('--tftp-port', type=int, default=59)
    parser.add_argument('--target-id', default='ARINC_1')
    parser.add_argument('--thw-id', default='ARINC')
    parser.add_argument('--serial', default='TEST001', help='serial number expected in the LCL')
    parser.add_argument('--timeout', type=int, default=5, help='socket timeout in seconds')
    parser.add_argument('--soak', type=int, default=0, help='extra upload+download cycles for memory checks')
    parser.add_argument('--bind', default='0.0.0.0', help='local address to listen on (PC NIC facing the board)')
    sys.exit(run(parser.parse_args()))


if __name__ == '__main__':
    main()
