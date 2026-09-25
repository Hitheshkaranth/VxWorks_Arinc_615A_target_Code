#!/usr/bin/env python3
"""Independent UDP/TFTP peer exercising real target operations on loopback.

Python standard library only. No simulated operating-system APIs are used.
"""
import argparse
import json
import socket
import struct
import subprocess
import tempfile
import threading
import time
from pathlib import Path

# vxworks_target_test.py reuses this peer against a real board and overrides
# these to listen on the LAN interface with a longer network timeout.
BIND_ADDRESS = '127.0.0.1'
SOCKET_TIMEOUT = 3


def udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((BIND_ADDRESS, 0))
    sock.settimeout(SOCKET_TIMEOUT)
    return sock


def packet(opcode, block):
    return struct.pack('!HH', opcode, block)


def request(opcode, name, options=None):
    data = struct.pack('!H', opcode) + name.encode() + b'\0octet\0'
    for key, value in (options or {}).items():
        data += key.encode() + b'\0' + str(value).encode() + b'\0'
    return data


def checked_recv(sock):
    data, remote = sock.recvfrom(65536)
    if len(data) < 2:
        raise AssertionError('Truncated TFTP packet')
    if data[:2] == b'\0\5':
        raise AssertionError('TFTP ERROR: ' + repr(data))
    return data, remote


def read_file(remote, name, options=None, drop_first=False):
    with udp() as sock:
        sock.sendto(request(1, name, options), remote)
        received = bytearray()
        expected = 1
        while True:
            data, peer = checked_recv(sock)
            opcode = struct.unpack('!H', data[:2])[0]
            if opcode == 6:
                sock.sendto(packet(4, 0), peer)
                continue
            assert opcode == 3
            if drop_first:
                # Deliberately lose one DATA/ACK exchange; require retransmission.
                drop_first = False
                continue
            block = struct.unpack('!H', data[2:4])[0]
            if block == expected:
                received.extend(data[4:])
                expected += 1
            sock.sendto(packet(4, block), peer)
            if len(data) < 516:
                return bytes(received)


def write_file(remote, name, data):
    with udp() as sock:
        sock.sendto(request(2, name), remote)
        response, peer = checked_recv(sock)
        assert response == packet(4, 0), response
        for offset in range(0, len(data) + 1, 512):
            block = offset // 512 + 1
            sock.sendto(packet(3, block) + data[offset:offset+512], peer)
            response, source = checked_recv(sock)
            assert source == peer and response == packet(4, block), response


class Peer:
    def __init__(self, files):
        self.sock = udp()
        self.sock.settimeout(0.1)
        self.files = files
        self.received = []
        self.errors = []
        self.workers = []
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    @property
    def port(self):
        return self.sock.getsockname()[1]

    def run(self):
        while not self.stopping.is_set():
            try:
                data, peer = self.sock.recvfrom(65536)
            except socket.timeout:
                continue
            worker = threading.Thread(target=self.transfer, args=(data, peer))
            self.workers.append(worker)
            worker.start()

    def transfer(self, data, peer):
        try:
            op = struct.unpack('!H', data[:2])[0]
            name = data[2:].split(b'\0')[0].decode()
            with udp() as transfer:
                if op == 2:
                    transfer.sendto(packet(4, 0), peer)
                    content = bytearray()
                    expected = 1
                    while True:
                        part, source = checked_recv(transfer)
                        assert source == peer and part[:2] == b'\0\3'
                        block = struct.unpack('!H', part[2:4])[0]
                        if block == expected:
                            content.extend(part[4:])
                            expected += 1
                        transfer.sendto(packet(4, block), peer)
                        if len(part) < 516:
                            self.received.append((name, bytes(content)))
                            return
                elif op == 1:
                    content = self.files[name]
                    for offset in range(0, len(content) + 1, 512):
                        block = offset // 512 + 1
                        transfer.sendto(packet(3, block) + content[offset:offset+512], peer)
                        ack, source = checked_recv(transfer)
                        assert source == peer and ack == packet(4, block), ack
                else:
                    raise AssertionError('Unexpected request opcode ' + str(op))
        except Exception as error:
            self.errors.append(repr(error))

    def wait(self, predicate, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assert not self.errors, self.errors
            for name, data in list(self.received):
                if predicate(name, data):
                    return data
            time.sleep(0.01)
        raise AssertionError('Missing expected response; received ' + repr([(n, d[:12]) for n, d in self.received]))

    def close(self):
        self.stopping.set()
        self.thread.join(2)
        self.sock.close()
        for worker in self.workers:
            worker.join(4)
            assert not worker.is_alive(), 'TFTP worker did not stop'
        assert not self.errors, self.errors


def string(value):
    raw = value.encode() + b'\0'
    return bytes([len(raw)]) + raw


def protocol(body):
    return struct.pack('!IH', 6 + len(body), 0x4134) + body


def run_suite(runner):
    with tempfile.TemporaryDirectory(prefix='arinc-transfer-') as directory:
        root = Path(directory)
        subprocess.run([runner, '--fixtures', str(root / 'files')], check=True)
        files = {p.name: p.read_bytes() for p in (root / 'files').iterdir()}
        (root / 'upload').mkdir()
        with udp() as reservation:
            find_port = reservation.getsockname()[1]
        with udp() as reservation:
            target_port = reservation.getsockname()[1]
        config = {
            'version': 'Arinc615a34', 'status_transmission_rate': 1,
            'arinc_615a': {'local_tftp_address': '127.0.0.1', 'dlp_retries': 1,
                'tftp': {'port': target_port, 'timeout': 1, 'retries': 2},
                'protocol_file_logging': False},
            'arinc_615a_find': {'local_find_address': '127.0.0.1', 'find_port': find_port},
            'find_information': [{'thwId': 'TEST', 'thwTypeName': 'THA', 'thwPosition': '1',
                'literalName': 'Integration test', 'manufacturerCode': 'UVDR'}],
            'targets_configuration': [{'target_id': 'TEST_1',
                'information_operation': {'enabled': True, 'targets_hardware': {'target_hardware': {
                    'literal_name': 'Test hardware', 'serial_number': 'SN001',
                    'part_numbers': [{'part_number': 'DEMO-PN', 'amendment': '', 'part_designation': 'Test payload'}]}}},
                'upload_operation': {'enabled': True, 'directory': str(root / 'upload'), 'checksum_option': False},
                'media_defined_download_operation': {'enabled': True, 'directories': {'directory': str(root / 'files')}},
                'operator_defined_download_operation': {'enabled': True, 'directories': {'directory': str(root / 'files')}}}]
        }
        config_file = root / 'config.json'
        config_file.write_text(json.dumps(config))
        with (root / 'target.log').open('w+') as log:
            proc = subprocess.Popen([runner, str(config_file)], stdin=subprocess.PIPE, stdout=log, stderr=log, text=True)
            peer = Peer(files)
            remote = ('127.0.0.1', target_port)
            try:
                with udp() as probe:
                    probe.settimeout(0.1)
                    for _ in range(50):
                        probe.sendto(b'\0\1\0\x10', ('127.0.0.1', find_port))
                        try:
                            data, _ = probe.recvfrom(2048)
                            assert b'TEST' in data
                            break
                        except socket.timeout:
                            assert proc.poll() is None, 'Target exited during startup'
                    else:
                        raise AssertionError('FIND did not answer')
                print('PASS: FIND over UDP')

                def begin(extension, drop_first=False):
                    peer.received.clear()
                    initial = read_file(remote, 'TEST_1.' + extension, {'port': peer.port}, drop_first)
                    assert len(initial) >= 8 and initial[6:8] == b'\0\1', initial

                begin('LCI', drop_first=True)
                information = peer.wait(lambda name, data: name.endswith('.LCL'))
                assert b'DEMO-PN' in information and b'SN001' in information
                print('PASS: Information accepted, lost DATA retried, and LCL transferred')
                time.sleep(0.1)

                begin('LUI')
                peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\1')
                write_file(remote, 'TEST_1.LUR', protocol(b'\0\1' + string('demo.LUH') + string('DEMO-PN')))
                peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\3')
                assert (root / 'upload' / 'payload.bin').read_bytes() == files['payload.bin']
                print('PASS: Upload, ARINC 665 load header, 4097-byte payload, completed status')
                time.sleep(0.1)

                begin('LND')
                peer.wait(lambda n, d: n.endswith('.LNS'))
                write_file(remote, 'TEST_1.LNR', protocol(b'\0\1' + string('payload.bin') + b'\0'))
                payload = peer.wait(lambda n, d: n == 'payload.bin')
                assert payload == files['payload.bin']
                peer.wait(lambda n, d: n.endswith('.LNS') and d[6:8] == b'\0\3')
                print('PASS: Media Defined Download payload and completed status')
                time.sleep(0.1)

                begin('LNO')
                listing = peer.wait(lambda n, d: n.endswith('.LNL'))
                assert b'payload.bin' in listing
                write_file(remote, 'TEST_1.LNA', protocol(b'\0\1' + string('payload.bin')))
                payload = peer.wait(lambda n, d: n == 'payload.bin')
                assert payload == files['payload.bin']
                peer.wait(lambda n, d: n.endswith('.LNS') and d[6:8] == b'\0\3')
                print('PASS: Operator Defined Download listing, selection, payload and completed status')
                time.sleep(0.1)

                # Malformed packets must not stop the process or poison FIND.
                with udp() as probe:
                    probe.sendto(b'\0', ('127.0.0.1', find_port))
                    probe.sendto(b'\0\1\0\x10', ('127.0.0.1', find_port))
                    response, _ = probe.recvfrom(2048)
                    assert b'TEST' in response
                print('PASS: Malformed FIND ignored; next valid request answered')

                peer.files['bad.LUH'] = b'bad'
                for header in ('empty.LUH', 'bad.LUH', 'traversal.LUH'):
                    begin('LUI')
                    peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\1')
                    write_file(remote, 'TEST_1.LUR', protocol(b'\0\1' + string(header) + string('DEMO-PN')))
                    peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\x10\x03')
                    assert proc.poll() is None
                    time.sleep(0.1)
                assert not (root / 'escape.bin').exists()
                print('PASS: Empty, malformed and path-traversal load headers rejected; server survives')

                original = files['payload.bin']
                for bad_payload in (b'X' + original[1:], original[:-1]):
                    peer.files['payload.bin'] = bad_payload
                    begin('LUI')
                    peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\1')
                    write_file(remote, 'TEST_1.LUR', protocol(b'\0\1' + string('demo.LUH') + string('DEMO-PN')))
                    peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\x10\x03')
                    time.sleep(0.1)
                peer.files['payload.bin'] = original
                begin('LUI')
                peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\1')
                write_file(remote, 'TEST_1.LUR', protocol(b'\0\1' + string('demo.LUH') + string('DEMO-PN')))
                peer.wait(lambda n, d: n.endswith('.LUS') and d[6:8] == b'\0\3')
                assert (root / 'upload' / 'payload.bin').read_bytes() == original
                print('PASS: Corrupt and truncated uploads rejected; subsequent valid upload succeeds')
            except Exception:
                log.flush()
                log.seek(0)
                print(log.read())
                raise
            finally:
                if proc.poll() is None:
                    try:
                        proc.communicate('stop\n', timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate()
                        raise AssertionError('Target failed to stop')
                peer.close()
            assert proc.returncode == 0, proc.returncode
            print('PASS: Target task stopped cleanly')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    run_suite(parser.parse_args().runner)
