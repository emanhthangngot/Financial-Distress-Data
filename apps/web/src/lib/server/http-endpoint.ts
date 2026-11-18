import "server-only";

export function absoluteHttpUrl(value: string | undefined, token?: string | null): string | null {
  if (
    !value ||
    !/^https?:\/\/[^/]/i.test(value) ||
    /[\s\\#]/u.test(value) ||
    [...value].some((character) => character.charCodeAt(0) < 32 || character === "\x7f")
  ) {
    return null;
  }
  const authority = value.split("/", 3)[2];
  if (authority?.includes("@") || authority?.includes("%") || authority?.endsWith(":")) return null;
  try {
    const url = new URL(value);
    if (url.search !== "") {
      const entries = [...url.searchParams];
      if (
        entries.length !== 1 ||
        entries[0]?.[0] !== "api-version" ||
        !/^\d{4}-\d{2}-\d{2}(?:-preview)?$/u.test(entries[0][1])
      ) return null;
    }
    if (token && (
      !isBearerToken(token) ||
      (url.protocol !== "https:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))
    )) return null;
    return url.hostname && url.port !== "0" ? value : null;
  } catch {
    return null;
  }
}

function isBearerToken(value: string): boolean {
  return /^[A-Za-z0-9._~+/-]+=*$/u.test(value) && !/\s/u.test(value);
}
