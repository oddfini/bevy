"""Transport and envelope regressions; all exchanges are mocked, with no sockets."""

import contextlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from brp_client import Client, ProtocolError, RpcError, TransportError, main


def response(message, raw=False, status=200):
    stream = io.BytesIO(message if raw else json.dumps(message).encode())
    stream.status = status
    return stream


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.opener = Mock()
        self.factory = patch("brp_client.urllib.request.build_opener", return_value=self.opener)
        self.factory_mock = self.factory.start()
        self.addCleanup(self.factory.stop)
        self.client = Client()

    def envelope(self, **values):
        return {"jsonrpc": "2.0", "id": 1, "result": {"revision": 0}, **values}

    def test_valid_results_and_sequential_ids(self):
        self.opener.open.side_effect = [response(self.envelope()), response(self.envelope(id=2, result=None))]
        self.assertEqual(self.client.call("agent.state"), {"revision": 0})
        self.assertIsNone(self.client.call("agent.act", {"expectedRevision": 0}))
        calls = self.opener.open.call_args_list
        first, second = (json.loads(call.args[0].data) for call in calls)
        self.assertEqual((first["id"], second["id"]), (1, 2))
        self.assertNotIn("params", first)
        self.assertEqual(second["params"], {"expectedRevision": 0})
        self.assertEqual(calls[0].kwargs["timeout"], 5)

    def test_wrong_response_ids_fail(self):
        for value in (999, True, 1.0, "1", None):
            with self.subTest(value=value):
                self.opener.open.return_value = response(self.envelope(id=value))
                with self.assertRaisesRegex(ProtocolError, "id"):
                    Client().call("agent.state")

    def test_wrong_version_or_nonobject_fails(self):
        for message in (self.envelope(jsonrpc="1.0"), {"id": 1, "result": 0}, [], None):
            with self.subTest(message=message):
                self.opener.open.return_value = response(message)
                with self.assertRaisesRegex(ProtocolError, "2.0"):
                    Client().call("agent.state")

    def test_result_and_error_are_mutually_exclusive(self):
        for message in (self.envelope(error={"code": -32602, "message": "invalid"}), {"jsonrpc": "2.0", "id": 1}):
            self.opener.open.return_value = response(message)
            with self.assertRaisesRegex(ProtocolError, "exactly one"):
                Client().call("agent.state")

    def test_remote_error_preserves_code_and_data(self):
        error = {"code": -32602, "message": "stale", "data": {"revision": 3}}
        self.opener.open.return_value = response({"jsonrpc": "2.0", "id": 1, "error": error})
        with self.assertRaises(RpcError) as caught:
            self.client.call("agent.act", {"expectedRevision": 0})
        self.assertEqual(caught.exception.code, -32602)
        self.assertEqual(caught.exception.error, error)
        self.opener.open.assert_called_once()

    def test_malformed_error_fails(self):
        for error in (None, [], {}, {"code": True, "message": "bad"}, {"code": "-1", "message": "bad"}, {"code": -1, "message": 4}):
            self.opener.open.return_value = response({"jsonrpc": "2.0", "id": 1, "error": error})
            with self.assertRaisesRegex(ProtocolError, "error object"):
                Client().call("agent.state")

    def test_invalid_json_nonfinite_and_duplicate_keys_fail(self):
        for raw in (b"not json", b'\xff', b'{"jsonrpc":"2.0","id":1,"result":NaN}', b'{"jsonrpc":"2.0","id":1,"result":Infinity}', b'{"jsonrpc":"2.0","id":1,"result":1e999}', b'{"jsonrpc":"2.0","id":1,"id":1,"result":0}'):
            self.opener.open.return_value = response(raw, raw=True)
            with self.assertRaisesRegex(ProtocolError, "JSON"):
                Client().call("agent.state")

    def test_response_is_bounded(self):
        stream = response(b"x" * 128, raw=True)
        stream.read = Mock(wraps=stream.read)
        self.opener.open.return_value = stream
        with self.assertRaisesRegex(ProtocolError, "max_response_bytes"):
            Client(max_response_bytes=32).call("agent.state")
        stream.read.assert_called_once_with(33)

    def test_deeply_nested_json_fails_as_protocol_error(self):
        self.opener.open.return_value = response(b"[" * 2000 + b"0" + b"]" * 2000, raw=True)
        with self.assertRaisesRegex(ProtocolError, "JSON"):
            self.client.call("agent.state")
        nested = []
        for _ in range(2000):
            nested = [nested]
        self.opener.open.reset_mock()
        with self.assertRaisesRegex(ProtocolError, "request JSON"):
            self.client.call("agent.act", {"value": nested})
        self.opener.open.assert_not_called()

    def test_counter_entrypoint_does_not_create_rust_workspace_cache_member(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory) / "tools"
            tools.mkdir()
            for name in ("agent-loop.py", "brp_client.py", "maintenance.py"):
                shutil.copy2(Path(__file__).resolve().parent / name, tools / name)
            command = (
                "import runpy,sys; sys.pycache_prefix=None; "
                "entry=sys.argv[1]; sys.argv=[entry, '--help']; "
                "sys.path.insert(0, entry.rsplit('/',1)[0]); "
                "runpy.run_path(entry, run_name='__main__')"
            )
            run = subprocess.run([sys.executable, "-c", command, str(tools / "agent-loop.py")],
                                 capture_output=True, text=True,
                                 env={"PATH": os.environ.get("PATH", ""), "PYTHONNOUSERSITE": "1"})
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertFalse((tools / "__pycache__").exists())

    def test_action_transport_failure_never_retries(self):
        self.opener.open.side_effect = TimeoutError("late response")
        with self.assertRaises(TransportError):
            self.client.call("agent.act", {"action": "commit"})
        self.opener.open.assert_called_once()

    def test_http_failure_does_not_accept_json_success(self):
        self.opener.open.return_value = response(self.envelope(), status=503)
        with self.assertRaisesRegex(TransportError, "503"):
            self.client.call("agent.state")

    def test_invalid_request_never_opens_transport(self):
        for method, params in (("", None), (3, None), ("agent.act", True), ("agent.act", "action"), ("agent.act", {"value": math.nan}), ("agent.act", {"value": object()})):
            with self.assertRaises(ProtocolError):
                Client().call(method, params)
        self.opener.open.assert_not_called()

    def test_only_literal_loopback_http_urls(self):
        invalid = ("https://127.0.0.1/", "http://example.com/", "http://localhost/", "http://192.168.1.2/", "file:///tmp/rpc", "http://user:pass@127.0.0.1/", "http://127.0.0.1:0/", "http://127.0.0.1:65536/", "http://127.0.0.1:/", "http://127.0.0.1/?", "http://127.0.0.1/#", " http://127.0.0.1/", "http://[::1%25lo0]/")
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                Client(url)
        for url in ("http://127.0.0.1:15702/", "http://127.1.2.3:1234/rpc", "http://[::1]:15702/"):
            Client(url)

    def test_timeout_and_byte_limit_validation(self):
        for timeout in (0, -1, True, "5", math.nan, math.inf):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                Client(timeout=timeout)
        for limit in (0, -1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                Client(max_response_bytes=limit)

    def test_proxy_environment_is_disabled_and_redirects_are_blocked(self):
        with patch.dict(os.environ, {"HTTP_PROXY": "http://example.com:8080"}):
            Client()
        handlers = self.factory_mock.call_args.args
        proxy = next(handler for handler in handlers if isinstance(handler, urllib.request.ProxyHandler))
        redirect = next(handler for handler in handlers if isinstance(handler, urllib.request.HTTPRedirectHandler))
        self.assertEqual(proxy.proxies, {})
        self.assertIsNone(redirect.redirect_request(None, None, 302, "move", {}, "http://example.com/"))
        self.opener.open.side_effect = urllib.error.HTTPError(self.client.url, 302, "move", {}, io.BytesIO())
        with self.assertRaisesRegex(TransportError, "302"):
            self.client.call("agent.act", {})
        self.opener.open.assert_called_once()

    def test_cli_success_and_failure_are_json(self):
        self.opener.open.return_value = response(self.envelope())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["agent.state"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True, "result": {"revision": 0}})
        for args in ([], ["--timeout", "NaN", "agent.state"], ["agent.act", "--params", "NaN"], ["agent.act", "--params", "{"]):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(args)
            self.assertNotEqual(code, 0)
            self.assertFalse(json.loads(output.getvalue())["ok"])

    def test_cli_remote_and_transport_errors_are_json(self):
        remote = {"code": -32602, "message": "stale", "data": {"revision": 3}}
        for failure in (response({"jsonrpc": "2.0", "id": 1, "error": remote}), TimeoutError("late")):
            self.opener.open.side_effect = failure if isinstance(failure, Exception) else None
            self.opener.open.return_value = failure
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["agent.act", "--params", "{}"])
            result = json.loads(output.getvalue())
            self.assertNotEqual(code, 0)
            self.assertFalse(result["ok"])
            if not isinstance(failure, Exception):
                self.assertEqual(result["error"], remote)


if __name__ == "__main__":
    unittest.main()
