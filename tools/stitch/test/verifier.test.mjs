import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { runStitchVerify } from "../bin/verify.mjs";
import { verifyDesignExport } from "../src/verifier.mjs";

function hash(value) {
  return createHash("sha256").update(value).digest("hex");
}

function screenEntry(localId = "login", overrides = {}) {
  return {
    localId,
    projectId: "project-1",
    screenId: "screen-1",
    kind: "base",
    screenshot: `screenshots/${localId}.png`,
    screenshotSha256: hash("image"),
    html: `html/${localId}.html`,
    htmlSha256: hash("html"),
    exportedAt: "2026-07-15T00:00:00.000Z",
    ...overrides
  };
}

async function writeJson(path, value) {
  await writeFile(path, JSON.stringify(value));
}

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), "stitch-verify-"));
  await mkdir(join(root, "screenshots"));
  await mkdir(join(root, "html"));
  await writeFile(join(root, "screenshots", "login.png"), "image");
  await writeFile(join(root, "html", "login.html"), "html");
  const manifest = {
    version: 1,
    projectId: "project-1",
    screens: [screenEntry()]
  };
  const state = {
    projectId: "project-1",
    screens: {
      login: { screenId: "screen-1", kind: "base" }
    }
  };
  await writeJson(join(root, "manifest.json"), manifest);
  await writeJson(join(root, "generation-state.json"), state);
  return { root, manifest, state };
}

test("verifyDesignExport accepts complete matching files", async () => {
  const { root } = await fixture();
  assert.deepEqual(
    await verifyDesignExport(root, ["login"], ["secret-value"]),
    { screenCount: 1 }
  );
});

test("verifyDesignExport rejects a missing required screen", async () => {
  const { root } = await fixture();
  await assert.rejects(
    () => verifyDesignExport(root, ["login", "bind"], []),
    /Missing exported screens: bind/
  );
});

test("verifyDesignExport rejects leaked secrets", async () => {
  const { root } = await fixture();
  await writeFile(join(root, "html", "login.html"), "secret-value");
  await assert.rejects(
    () => verifyDesignExport(root, ["login"], ["secret-value"]),
    /Forbidden secret value found/
  );
});

test("verifyDesignExport requires exact screen id sets", async t => {
  const cases = [
    ["unexpected manifest id", /Unexpected exported screens: extra/, data => {
      data.manifest.screens.push(screenEntry("extra"));
      data.state.screens.extra = { screenId: "screen-extra", kind: "base" };
    }],
    ["duplicate manifest id", /Duplicate exported screens: login/, data => {
      data.manifest.screens.push(screenEntry());
    }],
    ["missing state id", /Missing state screens: login/, data => {
      delete data.state.screens.login;
    }],
    ["unexpected state id", /Unexpected state screens: extra/, data => {
      data.state.screens.extra = { screenId: "screen-extra", kind: "base" };
    }],
    ["duplicate expected id", /Duplicate expected screens: login/, () => {}, ["login", "login"]]
  ];

  for (const [name, expectedError, mutate, expectedIds = ["login"]] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      mutate(data);
      await writeJson(join(data.root, "manifest.json"), data.manifest);
      await writeJson(join(data.root, "generation-state.json"), data.state);
      await assert.rejects(
        () => verifyDesignExport(data.root, expectedIds, [], () => {}),
        expectedError
      );
    });
  }
});

test("verifyDesignExport cross-checks manifest and state fields", async t => {
  const cases = [
    ["state project", /Project id mismatch/, data => {
      data.state.projectId = "project-2";
    }],
    ["entry project", /Manifest project id mismatch: login/, data => {
      data.manifest.screens[0].projectId = "project-2";
    }],
    ["screen id", /Screen id mismatch: login/, data => {
      data.manifest.screens[0].screenId = "screen-2";
    }],
    ["kind", /Screen kind mismatch: login/, data => {
      data.manifest.screens[0].kind = "variant";
    }],
    ["empty screen id", /Invalid screen id: login/, data => {
      data.manifest.screens[0].screenId = "";
      data.state.screens.login.screenId = "";
    }],
    ["invalid kind", /Invalid screen kind: login/, data => {
      data.manifest.screens[0].kind = "other";
      data.state.screens.login.kind = "other";
    }]
  ];

  for (const [name, expectedError, mutate] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      mutate(data);
      await writeJson(join(data.root, "manifest.json"), data.manifest);
      await writeJson(join(data.root, "generation-state.json"), data.state);
      await assert.rejects(
        () => verifyDesignExport(data.root, ["login"], [], () => {}),
        expectedError
      );
    });
  }
});

test("verifyDesignExport validates manifest structure", async t => {
  const cases = [
    ["version", /Invalid manifest version/, data => {
      data.manifest.version = 2;
    }],
    ["project id", /Invalid manifest project id/, data => {
      data.manifest.projectId = "";
      data.state.projectId = "";
    }],
    ["screens", /Invalid manifest screens/, data => {
      data.manifest.screens = {};
    }]
  ];

  for (const [name, expectedError, mutate] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      mutate(data);
      await writeJson(join(data.root, "manifest.json"), data.manifest);
      await writeJson(join(data.root, "generation-state.json"), data.state);
      await assert.rejects(
        () => verifyDesignExport(data.root, ["login"], [], () => {}),
        expectedError
      );
    });
  }
});

test("verifyDesignExport rejects screenshot and HTML hash mismatches", async t => {
  for (const [name, path, expectedError] of [
    ["screenshot", "screenshots/login.png", /Screenshot hash mismatch: login/],
    ["HTML", "html/login.html", /HTML hash mismatch: login/]
  ]) {
    await t.test(name, async () => {
      const { root } = await fixture();
      await writeFile(join(root, path), "tampered");
      await assert.rejects(
        () => verifyDesignExport(root, ["login"], [], () => {}),
        expectedError
      );
    });
  }
});

test("verifyDesignExport scans every raw buffer before hashes", async t => {
  const secret = "fake-test-secret";
  const cases = [
    ["manifest", async data => {
      data.manifest.note = secret;
      await writeJson(join(data.root, "manifest.json"), data.manifest);
    }],
    ["state", async data => {
      data.state.note = secret;
      await writeJson(join(data.root, "generation-state.json"), data.state);
    }],
    ["screenshot", data => writeFile(join(data.root, "screenshots/login.png"), secret)],
    ["HTML", data => writeFile(join(data.root, "html/login.html"), secret)]
  ];

  for (const [name, leak] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      await leak(data);
      await assert.rejects(
        () => verifyDesignExport(data.root, ["login"], [secret], () => {}),
        error => {
          assert.match(error.message, /Forbidden secret value found/);
          assert.equal(error.message.includes(secret), false);
          return true;
        }
      );
    });
  }
});

test("verifyDesignExport scans decoded JSON keys and values before logs", async t => {
  const secret = "decoded-test-secret";
  const encodedSecret = [...secret]
    .map(character => "\\u" + character.charCodeAt(0).toString(16).padStart(4, "0"))
    .join("");
  const cases = [
    ["project id", data => {
      data.manifest.projectId = secret;
      data.manifest.screens[0].projectId = secret;
      data.state.projectId = secret;
    }],
    ["screen id", data => {
      data.manifest.screens[0].screenId = secret;
      data.state.screens.login.screenId = secret;
    }],
    ["extra string value", data => {
      data.manifest.metadata = { note: secret };
    }],
    ["extra object key", data => {
      data.state.metadata = { [secret]: "safe" };
    }]
  ];

  for (const [name, mutate] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      mutate(data);
      const manifestJson = JSON.stringify(data.manifest).replaceAll(
        secret,
        encodedSecret
      );
      const stateJson = JSON.stringify(data.state).replaceAll(
        secret,
        encodedSecret
      );
      assert.equal(manifestJson.includes(secret), false);
      assert.equal(stateJson.includes(secret), false);
      await writeFile(join(data.root, "manifest.json"), manifestJson);
      await writeFile(join(data.root, "generation-state.json"), stateJson);
      const lines = [];
      await assert.rejects(
        () => verifyDesignExport(
          data.root,
          ["login"],
          [secret],
          line => lines.push(line)
        ),
        /Forbidden secret value found/
      );
      assert.equal(lines.join("\n").includes(secret), false);
    });
  }
});

test("verifyDesignExport rejects unsafe paths before reading outside root", async t => {
  const cases = [
    ["absolute screenshot", "screenshot", "absolute"],
    ["traversal screenshot", "screenshot", "traversal"],
    ["wrong screenshot filename", "screenshot", "filename"],
    ["absolute HTML", "html", "absolute"],
    ["traversal HTML", "html", "traversal"],
    ["wrong HTML filename", "html", "filename"]
  ];

  for (const [name, field, mode] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      const outsideName = basename(data.root) + "-outside";
      const outsidePath = join(data.root, "..", outsideName);
      await writeFile(outsidePath, "outside-secret");
      data.manifest.screens[0][field] = mode === "absolute"
        ? outsidePath
        : mode === "traversal"
          ? "../" + outsideName
          : `${field === "html" ? "html" : "screenshots"}/wrong-name`;
      await writeJson(join(data.root, "manifest.json"), data.manifest);
      await assert.rejects(
        () => verifyDesignExport(
          data.root,
          ["login"],
          ["outside-secret"],
          () => {}
        ),
        error => {
          assert.match(error.message, /Invalid artifact path: login/);
          assert.doesNotMatch(error.message, /Forbidden secret value found/);
          return true;
        }
      );
    });
  }
});

test("verifyDesignExport rejects symlinks that resolve outside root", async t => {
  const secret = "outside-symlink-secret";
  const cases = [
    ["artifact symlink", async data => {
      const outsidePath = join(data.root, "..", basename(data.root) + "-image");
      await writeFile(outsidePath, secret);
      await rm(join(data.root, "screenshots/login.png"));
      await symlink(outsidePath, join(data.root, "screenshots/login.png"));
    }],
    ["parent directory symlink", async data => {
      const outsideRoot = join(data.root, "..", basename(data.root) + "-dir");
      await mkdir(outsideRoot);
      await writeFile(join(outsideRoot, "login.png"), secret);
      await rm(join(data.root, "screenshots"), { recursive: true });
      await symlink(outsideRoot, join(data.root, "screenshots"), "dir");
    }]
  ];

  for (const [name, linkOutside] of cases) {
    await t.test(name, async () => {
      const data = await fixture();
      data.manifest.screens[0].screenshotSha256 = hash(secret);
      await writeJson(join(data.root, "manifest.json"), data.manifest);
      await linkOutside(data);
      await assert.rejects(
        () => verifyDesignExport(
          data.root,
          ["login"],
          [secret],
          () => {}
        ),
        error => {
          assert.match(error.message, /Invalid artifact path: login/);
          assert.doesNotMatch(error.message, /Forbidden secret value found/);
          return true;
        }
      );
    });
  }
});

test("verifyDesignExport emits structured per-screen logs through writer", async () => {
  const { root } = await fixture();
  const lines = [];
  await verifyDesignExport(root, ["login"], [], line => lines.push(line));
  const events = lines.map(line => JSON.parse(line));
  assert.deepEqual(events.map(event => event.result), ["started", "ok"]);
  for (const event of events) {
    assert.equal(event.event, "stitch.verify.screen");
    assert.equal(event.projectId, "project-1");
    assert.equal(event.localId, "login");
    assert.equal(event.screenId, "screen-1");
    assert.equal(event.kind, "base");
    assert.equal(event.screenshotPath, "screenshots/login.png");
    assert.equal(event.htmlPath, "html/login.html");
    assert.equal(typeof event.durationMs, "number");
  }
});
test("runStitchVerify is cwd-independent and uses one writer", async () => {
  const originalCwd = process.cwd();
  const otherCwd = await mkdtemp(join(tmpdir(), "stitch-cwd-"));
  const lines = [];
  const write = line => lines.push(line);
  let received;
  process.chdir(otherCwd);
  try {
    const code = await runStitchVerify({
      env: {
        STITCH_API_KEY: "fake-cli-key",
        STITCH_ACCESS_TOKEN: "fake-cli-token"
      },
      write,
      async verify(root, expectedIds, forbiddenValues, verifierWrite) {
        received = { root, expectedIds, forbiddenValues, verifierWrite };
        verifierWrite(JSON.stringify({ event: "test.writer" }));
        return { screenCount: 20 };
      }
    });
    assert.equal(code, 0);
  } finally {
    process.chdir(originalCwd);
  }

  assert.match(received.root, /docs\/design\/stitch\/couple-cosmos\/?$/);
  assert.deepEqual(received.expectedIds, [
    "home-base", "home-emotion", "home-food", "home-memory", "login",
    "bind", "menu-list", "menu-detail", "recipe-list", "recipe-detail",
    "recipe-editor", "feed", "memories", "note-editor", "map", "ai-chat",
    "settings", "notification-center", "legal-privacy", "system-states"
  ]);
  assert.deepEqual(received.forbiddenValues, ["fake-cli-key", "fake-cli-token"]);
  assert.equal(received.verifierWrite, write);
  const finalEvents = lines.map(JSON.parse).filter(event => event.event === "stitch.verify");
  assert.equal(finalEvents.length, 1);
  assert.equal(finalEvents[0].result, "ok");
  assert.equal(finalEvents[0].screenCount, 20);
});

test("runStitchVerify emits one safe final error for forbidden content", async () => {
  const secret = "fake-cli-secret";
  const { root } = await fixture();
  await writeFile(join(root, "screenshots/login.png"), secret);
  const lines = [];
  const code = await runStitchVerify({
    outputRoot: root,
    expectedIds: ["login"],
    env: { STITCH_API_KEY: secret },
    write: line => lines.push(line)
  });
  assert.equal(code, 1);
  assert.equal(lines.join("\n").includes(secret), false);
  const events = lines.map(JSON.parse);
  const finalEvents = events.filter(event => event.event === "stitch.verify");
  assert.equal(finalEvents.length, 1);
  assert.equal(finalEvents[0].result, "error");
  assert.match(finalEvents[0].errorMessage, /Forbidden secret value found/);
  assert.doesNotMatch(finalEvents[0].errorMessage, /hash mismatch/);
});

test("verify CLI main guard emits one JSON error when docs are absent", async () => {
  const cwd = await mkdtemp(join(tmpdir(), "stitch-cli-"));
  const cliPath = fileURLToPath(new URL("../bin/verify.mjs", import.meta.url));
  const child = spawn(process.execPath, [cliPath], { cwd, env: {} });
  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8").on("data", chunk => {
    stdout += chunk;
  });
  child.stderr.setEncoding("utf8").on("data", chunk => {
    stderr += chunk;
  });
  const exitCode = await new Promise((resolveExit, rejectExit) => {
    child.once("error", rejectExit);
    child.once("close", resolveExit);
  });
  assert.equal(exitCode, 1);
  assert.equal(stdout, "");
  const lines = stderr.trim().split("\n");
  assert.equal(lines.length, 1);
  const event = JSON.parse(lines[0]);
  assert.equal(event.event, "stitch.verify");
  assert.equal(event.result, "error");
});
