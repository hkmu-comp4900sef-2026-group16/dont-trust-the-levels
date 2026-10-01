"""Minimal UE4.27 Python Remote Execution client.

Implements the same wire protocol as unreal-mcp-ue4's underlying
`unreal-remote-execution` library, decoded from UE4.27's own
PythonScriptRemoteExecution.cpp:

  - UDP multicast 239.0.0.1:6766, magic "ue_py", version 1
  - ping -> pong discovery
  - open_connection tells the editor our command_ip/command_port
  - editor dials BACK into our TCP server (6776)
  - command {command, unattended, exec_mode} -> command_result
    {success, command, result, output:[{type,output}]}
"""
import json
import socket
import struct
import threading
import time
import uuid

MAGIC = "ue_py"
VERSION = 1
MULTICAST_GROUP = "239.0.0.1"
MULTICAST_PORT = 6766
COMMAND_PORT = 6776

# --- PROJECT GUARD -----------------------------------------------------------
# Multicast discovery finds ANY listening UE editor on the machine, regardless
# of which project it has open. Running a script against the wrong project
# silently writes foreign asset paths into it (this actually happened: an
# old-project script rewrote the new project's flipbooks with /Game/DTF/...).
# Set EXPECTED_PROJECT (or pass expected_project=...) to make the client refuse
# to run unless the connected editor has that project open.
EXPECTED_PROJECT = None      # e.g. "DontTrustTheLevels"
ALLOW_ANY_PROJECT = True     # flip to False to force the guard globally


class UERemote:
    def __init__(self, command_port=COMMAND_PORT):
        self.node_id = str(uuid.uuid4())
        self.command_port = command_port
        self.editor_node = None
        self.conn = None                 # accepted TCP connection from editor
        self._pending = None             # (Event, result list)
        self._lock = threading.Lock()

    # ---------------- message helpers ----------------
    @staticmethod
    def _msg(mtype, source, dest=None, data=None):
        m = {"version": VERSION, "magic": MAGIC, "source": source, "type": mtype}
        if dest:
            m["dest"] = dest
        if data is not None:
            m["data"] = data
        return json.dumps(m).encode("utf-8")

    @staticmethod
    def _parse(raw):
        m = json.loads(raw.decode("utf-8").strip())
        if m.get("version") != VERSION or m.get("magic") != MAGIC:
            raise ValueError("bad magic/version")
        return m

    def _local_ip(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        return ip

    def _multicast(self, mtype, dest=None, data=None):
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        tx.sendto(self._msg(mtype, self.node_id, dest, data),
                  (MULTICAST_GROUP, MULTICAST_PORT))
        tx.close()

    # ---------------- discovery ----------------
    def discover(self, timeout=10.0):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rx.bind(("", MULTICAST_PORT))
        mreq = struct.pack("4sL", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
        rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        rx.settimeout(1.0)

        deadline = time.time() + timeout
        found = None
        while time.time() < deadline and found is None:
            try:
                self._multicast("ping")
            except OSError:
                pass
            try:
                while True:
                    data, addr = rx.recvfrom(65536)
                    try:
                        m = self._parse(data)
                    except (ValueError, json.JSONDecodeError):
                        continue
                    if m["type"] == "pong" and m["source"] != self.node_id:
                        found = {"node_id": m["source"], "data": m.get("data", {}),
                                 "addr": addr}
                        break
            except socket.timeout:
                continue
        rx.close()
        self.editor_node = found
        return found

    # ---------------- reader thread ----------------
    def _read_conn(self, conn):
        buf = b""
        try:
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
                # messages are one JSON object per send; try to parse
                try:
                    msg = self._parse(buf)
                except (ValueError, json.JSONDecodeError):
                    continue
                buf = b""
                if msg.get("type") == "command_result":
                    with self._lock:
                        if self._pending:
                            ev, holder = self._pending
                            holder.append(msg.get("data", {}))
                            ev.set()
                            self._pending = None
        except OSError:
            pass

    # ---------------- connect ----------------
    def connect(self, timeout=10.0, expected_project=None):
        node = self.discover(timeout)
        if not node:
            raise RuntimeError("no editor responded to multicast ping")

        # --- project guard: refuse to touch the wrong project ---
        want = expected_project or EXPECTED_PROJECT
        got = node["data"].get("project_name")
        if want:
            if got != want:
                raise RuntimeError(
                    "WRONG PROJECT: connected editor has %r open, expected %r. "
                    "Refusing to run - this would write foreign asset paths." % (got, want))
        elif not ALLOW_ANY_PROJECT:
            raise RuntimeError(
                "no expected project set and ALLOW_ANY_PROJECT is False "
                "(connected editor has %r open)" % got)

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.command_port))
        srv.listen(1)

        self._multicast("open_connection", node["node_id"],
                        {"command_ip": self._local_ip(), "command_port": self.command_port})

        srv.settimeout(15)
        conn, addr = srv.accept()
        srv.close()
        self.conn = conn
        t = threading.Thread(target=self._read_conn, args=(conn,), daemon=True)
        t.start()
        return node, addr

    # ---------------- execution ----------------
    def run(self, code, mode="ExecuteFile", timeout=60):
        if self.conn is None:
            raise RuntimeError("not connected")
        msg = self._msg("command", self.node_id, self.editor_node["node_id"],
                        {"command": code, "unattended": True, "exec_mode": mode})
        ev = threading.Event()
        holder = []
        with self._lock:
            self._pending = (ev, holder)
        self.conn.sendall(msg)
        if not ev.wait(timeout):
            with self._lock:
                self._pending = None
            raise TimeoutError("editor did not answer within %ss" % timeout)
        return holder[0]


def main():
    ue = UERemote()
    node, addr = ue.connect(timeout=10)
    print("EDITOR:", node["data"].get("engine_version"), "|", node["data"].get("project_name"))
    print("CONNECTED FROM:", addr)

    res = ue.run('import unreal\n'
                 'print("HELLO-FROM-EDITOR", unreal.SystemLibrary.get_engine_version())')
    print("SUCCESS:", res.get("success"))
    for entry in res.get("output", []):
        print("  [%s] %s" % (entry.get("type"), entry.get("output", "").rstrip()))
    print("RESULT:", repr(res.get("result"))[:200])


if __name__ == "__main__":
    main()