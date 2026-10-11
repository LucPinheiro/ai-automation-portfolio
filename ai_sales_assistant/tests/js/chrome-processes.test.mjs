// The browser-test cleanup must only ever identify the test run's own Chrome processes.
// Pure tests on fake process lists: no real process is queried or touched here.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { isOwnTestProfile, testBrowserPids, userDataDir } from "../e2e/chrome_processes.mjs";

const TEMP = "C:\\Users\\ana\\AppData\\Local\\Temp";
const OWN = `${TEMP}\\e2e-chrome-AbC123`;
const OTHER_RUN = `${TEMP}\\e2e-chrome-ZzZ999`;
const CHROME = '"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"';

const processes = [
  // This test run: the browser (unquoted dir) and its children (quoted dir, no --headless flag).
  { ProcessId: 101, CommandLine: `${CHROME} --headless=new --user-data-dir=${OWN} about:blank` },
  { ProcessId: 102, CommandLine: `${CHROME} --type=renderer --user-data-dir="${OWN}" --lang=es` },
  { ProcessId: 103, CommandLine: `${CHROME} --type=utility --user-data-dir="${OWN}"` },
  { ProcessId: 104, CommandLine: `${CHROME} --type=crashpad-handler --user-data-dir=${OWN} --monitor-self` },
  // The user's own Chrome: default profile, explicit "User Data" profile, and a child process.
  { ProcessId: 201, CommandLine: `${CHROME} --restore-last-session` },
  { ProcessId: 202, CommandLine: `${CHROME} --user-data-dir="C:\\Users\\ana\\AppData\\Local\\Google\\Chrome\\User Data"` },
  { ProcessId: 203, CommandLine: `${CHROME} --type=renderer --lang=es` },
  // A user's Chrome that happens to run headless, and one with a profile in the temp folder.
  { ProcessId: 204, CommandLine: `${CHROME} --headless=new --user-data-dir=${TEMP}\\my-profile` },
  { ProcessId: 205, CommandLine: `${CHROME} --user-data-dir=${TEMP}` },
  // Another (parallel) test run: not this run's processes either.
  { ProcessId: 301, CommandLine: `${CHROME} --headless=new --user-data-dir=${OTHER_RUN}` },
  // Processes whose command line cannot be read (other users, elevated): never matched.
  { ProcessId: 401, CommandLine: null },
  { ProcessId: 402 },
];

describe("testBrowserPids", () => {
  test("finds every process of this run's browser, including children without --headless", () => {
    assert.deepEqual(testBrowserPids(OWN, processes, TEMP), [101, 102, 103, 104]);
  });

  test("never matches the user's Chrome", () => {
    const pids = testBrowserPids(OWN, processes, TEMP);
    for (const pid of [201, 202, 203, 204, 205, 401, 402]) assert.ok(!pids.includes(pid), `pid ${pid}`);
  });

  test("never matches another test run", () => {
    assert.ok(!testBrowserPids(OWN, processes, TEMP).includes(301));
  });

  test("Windows may report the path in another case: still the same profile", () => {
    const reported = [{ ProcessId: 501, CommandLine: `${CHROME} --type=gpu-process --user-data-dir="${OWN.toUpperCase()}"` }];
    assert.deepEqual(testBrowserPids(OWN, reported, TEMP.toLowerCase()), [501]);
  });

  test("the profile passed in must be exactly the folder the run created (stricter is safer)", () => {
    assert.equal(isOwnTestProfile(`${TEMP}\E2E-CHROME-ABC123`, TEMP), false);
  });

  for (const profile of [
    "",
    TEMP,
    `${TEMP}\\`,
    `${TEMP}\\e2e-chrome-`,
    `${TEMP}\\e2e-chrome-*`,
    `${TEMP}\\e2e-chrome-AbC12`,
    `${TEMP}\\e2e-chrome-AbC1234`,
    `${TEMP}\\my-profile`,
    "C:\\Users\\ana\\AppData\\Local\\Google\\Chrome\\User Data",
    `C:\\Other\\e2e-chrome-AbC123`,
    `${TEMP}\\nested\\e2e-chrome-AbC123`,
  ]) {
    test(`refuses an invalid or foreign profile: ${JSON.stringify(profile)}`, () => {
      assert.equal(isOwnTestProfile(profile, TEMP), false);
      // Even with a process list that would contain such a profile, nothing is returned.
      const everything = processes.concat([{ ProcessId: 999, CommandLine: `${CHROME} --user-data-dir=${profile}` }]);
      assert.deepEqual(testBrowserPids(profile, everything, TEMP), []);
    });
  }
});

describe("userDataDir", () => {
  test("reads quoted and unquoted values", () => {
    assert.equal(userDataDir(`x --user-data-dir=${OWN} y`), OWN);
    assert.equal(userDataDir(`x --user-data-dir="${OWN}" y`), OWN);
  });

  test("a prefix of the profile is not the profile", () => {
    // e2e-chrome-AbC1234 must not be mistaken for e2e-chrome-AbC123.
    assert.notEqual(userDataDir(`x --user-data-dir=${OWN}4 y`).toLowerCase(), OWN.toLowerCase());
  });

  test("missing or unreadable command lines give no profile", () => {
    assert.equal(userDataDir(null), "");
    assert.equal(userDataDir(undefined), "");
    assert.equal(userDataDir("chrome.exe --type=renderer"), "");
  });
});
