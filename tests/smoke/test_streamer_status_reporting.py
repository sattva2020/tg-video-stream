import os
import sys
import importlib
import types
from types import SimpleNamespace

if "metrics" not in sys.modules:
    class _DummyMetricsCollector:
        def __init__(self, *args, **kwargs):
            pass

        def run_loop(self):
            return

    sys.modules["metrics"] = types.SimpleNamespace(MetricsCollector=_DummyMetricsCollector)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "streamer")))
streamer_main = importlib.import_module("main")


class DummyResponse(SimpleNamespace):
    pass


def test_report_streamer_status_posts_payload(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://test-backend")
    monkeypatch.setenv("STREAMER_STATUS_TOKEN", "stream-token")

    captured = {}

    def fake_patch(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse(status_code=200, text="ok")

    monkeypatch.setattr(streamer_main.requests, "patch", fake_patch)

    streamer_main._report_streamer_status("track-123", "playing", duration=42)

    assert captured["url"].endswith("/api/playlist/track-123/status")
    assert captured["json"]["status"] == "playing"
    assert captured["json"]["duration"] == 42
    assert captured["headers"]["X-Streamer-Token"] == "stream-token"
    assert captured["timeout"] == 5


def test_report_streamer_status_skips_without_token(monkeypatch):
    monkeypatch.delenv("STREAMER_STATUS_TOKEN", raising=False)
    called = False

    def fake_patch(*args, **kwargs):
        nonlocal called
        called = True
        return DummyResponse(status_code=200, text="ok")

    monkeypatch.setattr(streamer_main.requests, "patch", fake_patch)

    streamer_main._report_streamer_status("track-456", "queued")

    assert not called
