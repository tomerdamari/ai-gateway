"""Minimal MCP client (Model Context Protocol, Streamable HTTP transport), standard library only.

Used by knowledge sources of kind "mcp": the gateway either calls one search tool on the server with the employee's
question (live search), or copies the server's text resources into the document index (sync). Everything an MCP
server returns is untrusted data: the caller scans and masks it before it reaches a model or the log.

The server address is typed by an administrator, so it could point the gateway at things it must never talk to
("server-side request forgery"): this machine itself, the cloud provider's metadata service, link-local devices.
Every connection resolves the name, refuses those addresses, then connects to the exact address it checked (a name
that changes its answer between the check and the connection can't slip through). Redirects are not followed and
system proxy settings are ignored. Private company addresses (10.x, 172.16-31.x, 192.168.x) are allowed, because
company MCP servers usually live there; ALLOW_PRIVATE_MCP=0 refuses them too.
"""
import http.client
import ipaddress
import json
import os
import socket
import urllib.error
import urllib.request

PROTOCOL = "2025-06-18"
TIMEOUT = 20
ALLOW_PRIVATE = os.environ.get("ALLOW_PRIVATE_MCP", "1").strip().lower() not in ("0", "false", "no", "off")
ALLOW_LOOPBACK = False  # tests only: the test suite's fake MCP server runs on this machine
METADATA = {ipaddress.ip_address("100.100.100.200"), ipaddress.ip_address("fd00:ec2::254")}  # Alibaba, AWS IPv6


class MCPError(Exception):
    pass


def blocked_ip(text):
    ip = ipaddress.ip_address(text.split("%")[0])
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    if ip.is_loopback:
        return not ALLOW_LOOPBACK
    if ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip.is_reserved or ip in METADATA:
        return True  # 169.254.169.254 (cloud metadata) is link-local
    return ip.is_private and not ALLOW_PRIVATE


def _connect(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, *rest):
    host, port = address[0], address[1]
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for *_, sa in infos:
        if blocked_ip(sa[0]):
            raise MCPError(f"address {sa[0]} is not allowed for MCP servers")
    return socket.create_connection((infos[0][4][0], port), timeout, source_address)


class _HTTP(http.client.HTTPConnection):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._create_connection = _connect


class _HTTPS(http.client.HTTPSConnection):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._create_connection = _connect  # TLS still checks the certificate against the name


class _HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_HTTP, req)


class _HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_HTTPS, req, context=self._context)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None  # a 3xx answer becomes an error instead of a request somewhere else


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _HTTPHandler, _HTTPSHandler, _NoRedirect)


def check_tool(tools, name, arg):
    """Why the live search may not call this tool with this argument, or None. Tools the server marks as changing
    data are refused (marked destructive, even if also marked read-only, or marked not read-only); a tool without such
    marks is allowed (MCP servers often don't mark them)."""
    t = next((t for t in tools if isinstance(t, dict) and t.get("name") == name), None)
    if not t:
        return "the server doesn't offer this tool"
    ann = t.get("annotations") or {}
    if ann.get("readOnlyHint") is False or ann.get("destructiveHint") is True:
        return "the tool can change data"
    props = (t.get("inputSchema") or {}).get("properties")
    if isinstance(props, dict) and props and arg not in props:
        return "the tool doesn't take this argument"
    return None


class Client:
    def __init__(self, url, token=""):
        self.url, self.session, self.next_id = url, None, 1
        self.headers = {"content-type": "application/json", "accept": "application/json, text/event-stream"}
        if token:
            self.headers["authorization"] = token if token.lower().startswith(("bearer ", "basic ")) else "Bearer " + token

    def _post(self, payload):
        headers = dict(self.headers)
        if self.session:
            headers["mcp-session-id"] = self.session
            headers["mcp-protocol-version"] = PROTOCOL
        req = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        try:
            with _OPENER.open(req, timeout=TIMEOUT) as r:
                self.session = r.headers.get("mcp-session-id") or self.session
                body, ctype = r.read(), r.headers.get("content-type", "")
        except urllib.error.HTTPError as e:
            raise MCPError(f"server answered HTTP {e.code}")
        except OSError as e:
            raise MCPError(f"server unreachable: {getattr(e, 'reason', e)}")
        if "id" not in payload:
            return None  # a notification: nothing to read
        # the answer comes either as plain JSON or as a short event stream with JSON in its data lines
        candidates = [body] if "event-stream" not in ctype else [
            line[5:].strip() for line in body.splitlines() if line.startswith(b"data:")]
        for raw in candidates:
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("id") == payload["id"]:
                if "error" in msg:
                    raise MCPError(str((msg["error"] or {}).get("message") or msg["error"])[:300])
                return msg.get("result") or {}
        raise MCPError("no answer from the server")

    def call(self, method, params=None):
        self.next_id += 1
        return self._post({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})

    def connect(self):
        result = self.call("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                          "clientInfo": {"name": "firegate", "version": "1.0"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def tools(self):
        return self.call("tools/list").get("tools") or []

    def resources(self):
        return self.call("resources/list").get("resources") or []

    def read(self, uri):
        """Text of one resource (text parts only; binary parts are returned base64 with their mime type)."""
        return self.call("resources/read", {"uri": uri}).get("contents") or []

    def run_tool(self, name, arguments):
        result = self.call("tools/call", {"name": name, "arguments": arguments})
        text = "\n\n".join(p.get("text", "") for p in result.get("content") or [] if p.get("type") == "text")
        if result.get("isError"):
            raise MCPError(text[:300] or "the tool reported an error")
        return text


def probe(url, token=""):
    """Connect and describe the server: name, tools (name, description, argument names), number of resources."""
    c = Client(url, token)
    info = c.connect()
    caps = info.get("capabilities") or {}
    tools = [{"name": t.get("name"), "description": (t.get("description") or "")[:200],
              "args": list(((t.get("inputSchema") or {}).get("properties") or {}).keys())}
             for t in (c.tools() if "tools" in caps else [])]
    resources = len(c.resources()) if "resources" in caps else 0
    return {"server": (info.get("serverInfo") or {}).get("name") or "", "tools": tools, "resources": resources}
