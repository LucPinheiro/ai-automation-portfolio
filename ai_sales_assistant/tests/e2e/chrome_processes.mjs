// Identifies the Chrome processes started by the browser tests, and nothing else.
// Pure matching logic (testable with fake process lists) plus one read-only process query.
//
// Rule: a process belongs to a test run only if its --user-data-dir is EXACTLY that run's own
// profile folder, freshly created with mkdtemp as <temp dir>/e2e-chrome-XXXXXX. Every process of a
// Chrome instance (browser, renderers, gpu, utilities, crashpad) carries that same --user-data-dir,
// while the user's own Chrome uses its normal "User Data" folder, so it can never match.
// No name patterns or wildcards are used anywhere.
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { basename, dirname } from "node:path";

const TEST_PROFILE_FOLDER = /^e2e-chrome-[A-Za-z0-9]{6}$/;
const USER_DATA_DIR = /--user-data-dir=(?:"([^"]+)"|(\S+))/;

export function isOwnTestProfile(profile, temp = tmpdir()) {
  return TEST_PROFILE_FOLDER.test(basename(profile)) && dirname(profile).toLowerCase() === temp.toLowerCase();
}

export function chromeProcesses() {
  // Read-only query: process ids and command lines of every chrome.exe.
  const script =
    "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress";
  const encoded = Buffer.from(script, "utf16le").toString("base64");
  const result = spawnSync("powershell", ["-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.status !== 0 || !result.stdout.trim()) return [];
  const parsed = JSON.parse(result.stdout);
  return Array.isArray(parsed) ? parsed : [parsed];
}

/** The --user-data-dir of a command line (quoted or not), or "" if it has none. */
export function userDataDir(commandLine) {
  const match = (commandLine ?? "").match(USER_DATA_DIR);
  return match ? (match[1] ?? match[2]) : "";
}

/** PIDs of the processes that belong to this test run's browser, identified exactly. */
export function testBrowserPids(profile, processes = chromeProcesses(), temp = tmpdir()) {
  if (!isOwnTestProfile(profile, temp)) return [];
  const own = profile.toLowerCase();
  return processes
    .filter(({ CommandLine }) => userDataDir(CommandLine).toLowerCase() === own)
    .map(({ ProcessId }) => ProcessId);
}

