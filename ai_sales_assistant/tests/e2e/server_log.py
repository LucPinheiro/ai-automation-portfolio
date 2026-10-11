"""Decides whether a failed browser scenario may be retried.

A retry is allowed only when the test server's own log proves that the requests Chrome was
waiting for never reached the server (an environmental stall between the test Chrome and the
local server, e.g. antivirus/firewall inspection), never for a failure inside the application.
"""

import json
import re

# Lines the harness prints when a page did not arrive: "[e2e] page /login did not load in 15 s; ..."
STALLED_PAGE = re.compile(r"\[e2e\] page (/\S*) did not load")
# Pending requests in the harness diagnostics: "GET /app"
PENDING_REQUEST = re.compile(r"^(GET|POST|PUT|DELETE|PATCH) (/\S*)$")


def requests_left_waiting(stdout: str, stderr: str) -> set[tuple[str, str]]:
    """(method, path) of the requests the browser was left waiting for, as reported by the harness."""
    waiting = {("GET", path) for path in STALLED_PAGE.findall(stderr)}
    for line in reversed(stdout.strip().splitlines()):
        try:
            report = json.loads(line)
        except ValueError:
            continue
        for request in report.get("diagnostics", {}).get("pendingRequests", []):
            match = PENDING_REQUEST.match(request)
            if match:
                waiting.add((match.group(1), match.group(2)))
        break
    return waiting


def server_received(log_since_attempt: str, method: str, path: str) -> bool:
    """True if uvicorn logged that request (it logs every response: '"GET /app HTTP/1.1" 303')."""
    path_only = path.split("?")[0]
    pattern = re.compile(rf'"{method} {re.escape(path_only)}(\?\S*)? HTTP/1\.[01]"')
    return bool(pattern.search(log_since_attempt))


def never_reached_server(stdout: str, stderr: str, log_since_attempt: str) -> set[tuple[str, str]]:
    """The stalled requests, if the log proves NONE of them reached the server; otherwise empty.

    Empty means "do not retry": either the harness reported no stalled request (so it is a real
    failure), or at least one of them did reach the server (so the server, not the network, is
    involved and the failure must be investigated).
    """
    waiting = requests_left_waiting(stdout, stderr)
    if not waiting or any(server_received(log_since_attempt, method, path) for method, path in waiting):
        return set()
    return waiting
