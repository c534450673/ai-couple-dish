const SENSITIVE_NAMES = [
  "apikey",
  "token",
  "authorization",
  "secret"
];

function sanitize(value, key = "") {
  if (key === "toJSON" || typeof value === "function") {
    return undefined;
  }
  const normalizedKey = key.toLowerCase().replace(/[^a-z0-9]/g, "");
  if (SENSITIVE_NAMES.some(name => normalizedKey.includes(name))) {
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
  const sanitizedFields = sanitize(fields);
  const result = sanitizedFields.result ?? "unknown";
  const durationMs = sanitizedFields.durationMs ?? 0;

  write(
    JSON.stringify({
      ...sanitizedFields,
      timestamp: new Date().toISOString(),
      event: event ?? "unknown",
      result,
      durationMs
    })
  );
}
