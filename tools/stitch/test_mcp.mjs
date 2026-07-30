import { Stitch, StitchToolClient } from "@google/stitch-sdk";
import { setGlobalDispatcher, ProxyAgent } from "undici";
const dispatcher = new ProxyAgent("http://127.0.0.1:7897");
setGlobalDispatcher(dispatcher);
const client = new StitchToolClient({
    apiKey: process.env.STITCH_API_KEY,
    baseUrl: "https://stitch.googleapis.com/mcp",
    timeout: 30000
});
async function run() {
    try {
        const response = await client.listTools();
        console.log(response);
    } catch(e) {
        console.error("FAIL:", e);
    } finally {
        await client.close();
    }
}
run();
