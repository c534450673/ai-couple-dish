import { Stitch, StitchToolClient } from "@google/stitch-sdk";

const REQUIRED_TOOLS = [
  "create_project",
  "generate_screen_from_text",
  "get_screen"
];

export function createStitchSdk(
  config,
  dependencies = { Stitch, StitchToolClient }
) {
  const client = new dependencies.StitchToolClient({
    apiKey: config.apiKey,
    baseUrl: config.host,
    timeout: 300000
  });
  return {
    sdk: new dependencies.Stitch(client),
    client
  };
}

export async function assertRequiredTools(client) {
  const response = await client.listTools();
  const names = response.tools.map(tool => tool.name);
  const missing = REQUIRED_TOOLS.filter(name => !names.includes(name));
  if (missing.length > 0) {
    throw new Error("Missing required Stitch tools: " + missing.join(", "));
  }
  return REQUIRED_TOOLS;
}
