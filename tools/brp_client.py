#!/usr/bin/env python3
"""A bounded JSON-RPC client for local Bevy development endpoints."""

import argparse
import http.client
import ipaddress
import json
import math
import urllib.error
import urllib.parse
import urllib.request


class ProtocolError(RuntimeError):
    """The request or response does not follow the supported JSON-RPC contract."""


class TransportError(RuntimeError):
    """The local HTTP exchange failed. An action may already have committed."""


class RpcError(RuntimeError):
    """A validated JSON-RPC error returned by the application."""

    def __init__(self, error):
        self.error = error
        self.code = error["code"]
        super().__init__(f"RPC error {self.code}: {error['message']}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"Non-finite JSON constant: {value}")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number exceeds the finite float range")
    return result


def _loads(value):
    return json.loads(value, object_pairs_hook=_object, parse_constant=_constant, parse_float=_float)


class Client:
    """Make one HTTP request per call. Socket timeouts never trigger a retry."""

    def __init__(self, url="http://127.0.0.1:15702/", timeout=5, max_response_bytes=1048576):
        if type(timeout) not in (int, float) or timeout <= 0 or not math.isfinite(timeout):
            raise ValueError("timeout must be a finite positive number")
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be a positive integer")
        if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
            raise ValueError("Use an HTTP URL with a literal loopback address")
        try:
            parts = urllib.parse.urlsplit(url)
            host, port = parts.hostname, parts.port
            valid = (parts.scheme == "http" and host is not None and "%" not in host
                     and ipaddress.ip_address(host).is_loopback
                     and parts.username is None and parts.password is None
                     and "?" not in url and "#" not in url and not parts.netloc.endswith(":")
                     and (port is None or 1 <= port <= 65535))
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Use HTTP with a literal loopback address, valid port, and no credentials, query, or fragment")
        self.url = url
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self._next_id = 1
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def call(self, method, params=None):
        if not isinstance(method, str) or not method:
            raise ProtocolError("method must be a nonempty string")
        if params is not None and not isinstance(params, (dict, list)):
            raise ProtocolError("params must be an object or array")
        request_id = self._next_id
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError) as error:
            raise ProtocolError(f"Invalid request JSON: {error}") from error
        self._next_id += 1
        request = urllib.request.Request(self.url, body, {"Content-Type": "application/json"})
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise TransportError(f"HTTP status {response.status}")
                raw = response.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as error:
            error.close()
            raise TransportError(f"HTTP status {error.code}") from error
        except (OSError, http.client.HTTPException) as error:
            raise TransportError(f"HTTP exchange failed: {error}") from error
        if len(raw) > self.max_response_bytes:
            raise ProtocolError("Response exceeds max_response_bytes")
        try:
            message = _loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError) as error:
            raise ProtocolError(f"Invalid response JSON: {error}") from error
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            raise ProtocolError("Expected a JSON-RPC 2.0 response object")
        if type(message.get("id")) is not int or message["id"] != request_id:
            raise ProtocolError("Response id does not match the request")
        if ("result" in message) == ("error" in message):
            raise ProtocolError("Response must contain exactly one of result or error")
        if "error" in message:
            error = message["error"]
            if not isinstance(error, dict) or type(error.get("code")) is not int or not isinstance(error.get("message"), str):
                raise ProtocolError("Expected an error object with integer code and string message")
            raise RpcError(error)
        return message["result"]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:15702/")
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("method", metavar="METHOD")
    parser.add_argument("--params", help="JSON object or array")
    try:
        args = parser.parse_args(argv)
        params = _loads(args.params) if args.params is not None else None
        result = Client(args.url, args.timeout).call(args.method, params)
        print(json.dumps({"ok": True, "result": result}, allow_nan=False))
        return 0
    except RpcError as error:
        failure = error.error
    except (ValueError, RecursionError, ProtocolError, TransportError) as error:
        failure = {"type": type(error).__name__, "message": str(error)}
    print(json.dumps({"ok": False, "error": failure}, allow_nan=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
