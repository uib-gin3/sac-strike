#!/usr/bin/env python3

# This file has been implemented with GLM-5.3-Flash on OpenCode

# strikeapi.py: the tiny stdlib clients shared by the strike- commands.
#
# A minimal RESP client to read redis from the host, a minimal etcd v3
# reader (JSON gateway), a plain http helper for the nodes and the
# hostname/port mapping of the workforce. Standard library only, just
# like the rest of the project.

import base64
import http.client
import json
import os
import socket
import time
import urllib.request
from urllib.parse import urlsplit

LEADER_KEY = 'strike/leader'

# The shared clock: strike-demo exports STRIKE_T0 so every tool narrates
# on the same timeline. A tool run standalone falls back to its own start.
_T0 = os.environ.get('STRIKE_T0')
_T0 = float(_T0) if _T0 else time.time()


def elapsed():
    """ Seconds since the shared clock started. """
    return time.time() - _T0


def elapsed_at(when):
    """ The shared-clock time of a wall clock timestamp. """
    return when - _T0


def wall_at(seconds):
    """ The wall clock time `seconds` after the shared clock started. """
    return _T0 + seconds


def stamp(text):
    """ One line of the narration: [xx.xs] text. """
    print(f"[{elapsed():6.1f}s] {text}", flush=True)


class Resp:
    """ A minimal Redis (RESP) client, just enough to read and clean. """

    def __init__(self, host, port, timeout=3.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.rfile = self.sock.makefile('rb')

    def command(self, *args):
        """ Send a command and read its single reply. """

        payload = f"*{len(args)}\r\n".encode()
        for arg in args:
            arg = str(arg).encode()
            payload += f"${len(arg)}\r\n".encode() + arg + b"\r\n"

        self.sock.sendall(payload)
        return self._reply()

    def _reply(self):
        line = self.rfile.readline()
        if not line:
            raise OSError("connection closed by redis")
        kind, rest = line[:1], line[1:-2]
        if kind == b'+':
            return rest.decode()
        if kind == b'-':
            raise RuntimeError(rest.decode())
        if kind == b':':
            return int(rest)
        if kind == b'$':
            length = int(rest)
            if length == -1:
                return None
            return self.rfile.read(length + 2)[:-2].decode('utf-8',
                                                           errors='replace')
        if kind == b'*':
            return [self._reply() for _ in range(int(rest))]
        raise OSError(f"bad RESP line: {line!r}")

    def close(self):
        self.sock.close()


def etcd_get(etcd, key):
    """ Read a key from etcd through the v3 JSON gateway. """

    payload = json.dumps({'key': base64.b64encode(key.encode()).decode()})
    http_request = urllib.request.Request(
        f"http://{etcd}/v3/kv/range", data=payload.encode(),
        headers={'Content-Type': 'application/json'})

    with urllib.request.urlopen(http_request, timeout=2.0) as reply:
        answer = json.loads(reply.read())

    kvs = answer.get('kvs') or []
    return base64.b64decode(kvs[0]['value']).decode() if kvs else None


def leader_name(etcd):
    """ The hostname of the leader.

    " The strike/leader key holds the endpoint (http://nodeN:12345),
    " the same format as the workforce entries; the narration speaks
    " of hostnames.
    """

    endpoint = etcd_get(etcd, LEADER_KEY)
    return urlsplit(endpoint).hostname if endpoint else None


def req(port, method, path, body=None, timeout=5.0):
    """ One plain HTTP request to localhost:port, returns (status, headers,
    " body). Headers come lowercased in a dict.
    """

    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        conn.request(method, path, body=body,
                     headers={'Content-Type': 'text/plain; charset=utf-8'}
                     if body else {})
        raw = conn.getresponse()
        return raw.status, {k.lower(): v for k, v in raw.getheaders()}, raw.read()
    finally:
        conn.close()


def nodes(count, port_base):
    """ The workforce as seen from the host: {hostname: published port}.
    " The compose maps nodeN to port_base + N - 1.
    """

    return {f"node{index + 1}": port_base + index for index in range(count)}
