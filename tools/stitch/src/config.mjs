const DEFAULT_HOST = "https://stitch.googleapis.com/mcp";

export function readStitchConfig(env = process.env) {
  const apiKey = String(env.STITCH_API_KEY || "").trim();
  if (!apiKey) {
    throw new Error(
      "STITCH_API_KEY must be provided through the process environment"
    );
  }

  return Object.freeze({
    apiKey,
    host: String(env.STITCH_HOST || DEFAULT_HOST).trim()
  });
}

export function publicConfig(config) {
  return Object.freeze({
    hasApiKey: Boolean(config.apiKey),
    host: config.host
  });
}
