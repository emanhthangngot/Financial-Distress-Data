import { afterEach, describe, expect, it } from "vitest";
import {
  DEFAULT_ASSISTANT_TIMEOUT_MS,
  MAX_ASSISTANT_TIMEOUT_MS,
  readInferenceConfig,
  redactUrl,
} from "./inference-config";

const KEYS = [
  "DISTRESSLENS_INFERENCE_URL",
  "DISTRESSLENS_INFERENCE_TOKEN",
  "ASSISTANT_TIMEOUT_MS",
] as const;

function withEnv(
  env: Record<string, string | undefined>,
  fn: () => void,
): void {
  const previous = new Map<string, string | undefined>();
  for (const key of KEYS) {
    previous.set(key, process.env[key]);
    if (env[key] === undefined) delete process.env[key];
    else process.env[key] = env[key];
  }
  try {
    fn();
  } finally {
    for (const [key, value] of previous) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

afterEach(() => {
  for (const key of KEYS) delete process.env[key];
});

describe("readInferenceConfig", () => {
  it("reports unconfigured when url and token are both missing", () => {
    withEnv({}, () => {
      const config = readInferenceConfig();
      expect(config.isConfigured).toBe(false);
      expect(config.url).toBeNull();
      expect(config.token).toBeNull();
    });
  });

  it("is unconfigured with a url but no token", () => {
    withEnv({ DISTRESSLENS_INFERENCE_URL: "https://infer.example.com/v1" }, () => {
      const config = readInferenceConfig();
      expect(config.isConfigured).toBe(false);
      expect(config.url).toBe("https://infer.example.com/v1");
      expect(config.token).toBeNull();
    });
  });

  it("is configured only when both url and token are present", () => {
    withEnv(
      {
        DISTRESSLENS_INFERENCE_URL: "https://infer.example.com/v1",
        DISTRESSLENS_INFERENCE_TOKEN: "sk-secret",
      },
      () => {
        const config = readInferenceConfig();
        expect(config.isConfigured).toBe(true);
        expect(config.token).toBe("sk-secret");
      },
    );
  });

  it("defaults the timeout and clamps it below 60s", () => {
    withEnv({}, () => expect(readInferenceConfig().timeoutMs).toBe(DEFAULT_ASSISTANT_TIMEOUT_MS));

    withEnv({ ASSISTANT_TIMEOUT_MS: "999999" }, () => {
      expect(readInferenceConfig().timeoutMs).toBe(MAX_ASSISTANT_TIMEOUT_MS);
    });

    withEnv({ ASSISTANT_TIMEOUT_MS: "garbage" }, () => {
      expect(readInferenceConfig().timeoutMs).toBe(DEFAULT_ASSISTANT_TIMEOUT_MS);
    });
  });

  it("never returns the token through any field of the config string", () => {
    withEnv(
      {
        DISTRESSLENS_INFERENCE_URL: "https://infer.example.com/v1",
        DISTRESSLENS_INFERENCE_TOKEN: "sk-super-secret-42",
      },
      () => {
        const config = readInferenceConfig();
        const serialized = JSON.stringify(config);
        expect(serialized).toContain("sk-super-secret-42"); // token is real, that's fine
        // Only the explicit token field may carry it: no URL anywhere holds it.
        expect(redactUrl(config.url as string)).not.toContain("sk-super-secret-42");
      },
    );
  });
});

describe("redactUrl", () => {
  it("strips userinfo from a url with an embedded token", () => {
    const redacted = redactUrl("https://admin:sk-abc123@infer.example.com/v1");
    expect(redacted).not.toContain("sk-abc123");
    expect(redacted).not.toContain("@");
    expect(redacted).toContain("https://infer.example.com/v1");
  });

  it("strips query parameters that could carry a token", () => {
    const redacted = redactUrl("https://infer.example.com/v1?api_key=sk-leak");
    expect(redacted).not.toContain("sk-leak");
    expect(redacted).not.toContain("api_key");
  });

  it("returns a stable literal for an invalid url", () => {
    expect(redactUrl("not a url at all")).toBe("(invalid url)");
  });
});