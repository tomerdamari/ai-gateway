"""Minimal MCP client (Model Context Protocol, Streamable HTTP transport), standard library only.

Used by knowledge sources of kind "mcp": the gateway either calls one search tool on the server with the employee's
question (live search), or copies the server's text resources into the document index (sync). Everything an MCP
server returns is untrusted data: the caller scans and masks it before it reaches a model or the log.
"""
import json
import urllib.error
import urllib.request

PROTOCOL = "2025-06-18"
TIMEOUT = 20


class MCPError(Exception):
    pass


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
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
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
                                          "clientInfo": {"name": "ai-gateway", "version": "1.0"}})
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
