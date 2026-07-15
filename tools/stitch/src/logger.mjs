const SENSITIVE_NAMES = new Set([
  "apikey",
  "api_key",
  "token",
  "accesstoken",
  "access_token",
  "authorization"
]);

function sanitize(value, key = "") {
  const normalizedKey = key.toLowerCase();
  if (SENSITIVE_NAMES.has(normalizedKey)) {
    return "[REDACTED]";
  }
  if (Array.isArray(value)) {
    return value.map(item => sanitize(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([name, item]) => [name, sanitize(item, name)])
    );
  }
  return value;
}

export function logEvent(
  event,
  fields = {},
  write = line => process.stderr.write(line + String.fromCharCode(10))
) {
  write(
    JSON.stringify({
      timestamp: new Date().toISOString(),
      event,
      ...sanitize(fields)
    })
  );
}
