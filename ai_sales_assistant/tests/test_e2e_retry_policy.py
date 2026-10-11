"""When may a browser scenario be retried? Only if the server log proves it never got the request."""

import json

from tests.e2e.server_log import never_reached_server, requests_left_waiting, server_received

LOG = (
    'INFO:     127.0.0.1:50001 - "GET /health HTTP/1.1" 200 OK\n'
    'INFO:     127.0.0.1:50002 - "GET /login HTTP/1.1" 200 OK\n'
    'INFO:     127.0.0.1:50003 - "POST /guest HTTP/1.1" 303 See Other\n'
    'INFO:     127.0.0.1:50004 - "GET /contacto?x=1 HTTP/1.1" 200 OK\n'
)


def harness_failure(pending: list[str]) -> str:
    return json.dumps({"harnessError": "Error: timeout", "diagnostics": {"pendingRequests": pending}})


def test_stalled_pages_and_pending_requests_are_collected() -> None:
    stderr = "[e2e] page /app did not load in 15 s; requesting it once more\n"

    waiting = requests_left_waiting(harness_failure(["GET /contacto", "POST /contacto"]), stderr)

    assert waiting == {("GET", "/app"), ("GET", "/contacto"), ("POST", "/contacto")}


def test_server_received_matches_method_and_path_exactly() -> None:
    assert server_received(LOG, "GET", "/login")
    assert server_received(LOG, "POST", "/guest")
    assert server_received(LOG, "GET", "/contacto")  # query string ignored
    assert not server_received(LOG, "POST", "/login")
    assert not server_received(LOG, "GET", "/log")  # no prefix matches
    assert not server_received(LOG, "GET", "/app")


def test_retry_when_the_log_proves_nothing_arrived() -> None:
    stderr = "[e2e] page /app did not load in 15 s; requesting it once more\n"

    assert never_reached_server(harness_failure(["GET /app"]), stderr, LOG) == {("GET", "/app")}


def test_no_retry_when_the_request_reached_the_server() -> None:
    # The server got it: the failure is not a network stall and must be investigated.
    assert never_reached_server(harness_failure(["GET /login"]), "", LOG) == set()


def test_no_retry_when_only_some_requests_were_lost() -> None:
    stderr = "[e2e] page /app did not load in 15 s; requesting it once more\n"

    assert never_reached_server(harness_failure(["GET /login"]), stderr, LOG) == set()


def test_no_retry_for_a_failure_without_stalled_requests() -> None:
    # e.g. an assertion or JavaScript error in the application: never retried.
    assert never_reached_server(harness_failure([]), "", LOG) == set()
    assert never_reached_server('{"card": {}}', "", LOG) == set()


def test_no_retry_when_the_harness_printed_nothing() -> None:
    assert never_reached_server("", "", LOG) == set()
