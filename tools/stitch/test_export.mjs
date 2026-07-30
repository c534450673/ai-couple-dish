import { runStitchExport } from "./bin/export.mjs";
import { setGlobalDispatcher, ProxyAgent } from "undici";
const dispatcher = new ProxyAgent({
  uri: "http://127.0.0.1:7897",
  requestTls: { timeout: 60000, rejectUnauthorized: false }
});
setGlobalDispatcher(dispatcher);
process.exitCode = await runStitchExport();
