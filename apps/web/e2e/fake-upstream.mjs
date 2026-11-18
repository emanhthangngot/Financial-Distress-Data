/**
 * Fixture-mode fake inference upstream, e2e-only.
 *
 * The assistant stream route points DISTRESSLENS_INFERENCE_URL at this server
 * so the evidence run can prove streaming, timeout, refusal and malformed
 * handling deterministically — without any real model, and without the test
 * suite ever importing this file into `src/`.
 *
 * Behaviour is selected by the glossary concept in the last user message:
 *   - quick ratio -> a refusal chunk, translated to policy_blocked
 *   - data drift -> a delay past ASSISTANT_TIMEOUT_MS, then a token
 *   - financial distress -> broken JSON, translated to MALFORMED_RESPONSE
 *   - otherwise -> a canned definition stream then finish
 */
"use strict";

import http from "node:http";

const port = Number(process.env.FAKE_UPSTREAM_PORT ?? 3322);
const received = new Set();

function sendEvent(res, chunk) {
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}

function finish(res) {
  sendEvent(res, { choices: [{ delta: {}, finish_reason: "stop" }] });
  res.end();
}

http
  .createServer((req, res) => {
    const url = new URL(req.url ?? "/", "http://127.0.0.1");
    if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("ok");
      return;
    }
    if (req.method === "GET" && url.pathname === "/received") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ seen: received.has(url.searchParams.get("id")) }));
      return;
    }

    if (req.method !== "POST") {
      res.writeHead(405, { "content-type": "text/plain" });
      res.end("method not allowed");
      return;
    }
    if (req.headers["x-correlation-id"]) received.add(req.headers["x-correlation-id"]);
    if (url.pathname !== "/v1/chat/completions" || url.search !== "") {
      res.writeHead(404).end();
      return;
    }
    if (req.headers.authorization !== "Bearer fake-e2e-token") {
      res.writeHead(401).end();
      return;
    }

    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      let question = "";
      try {
        const parsed = JSON.parse(body);
        if (parsed.model !== "fixture-glossary") {
          res.writeHead(400).end();
          return;
        }
        const messages = parsed.messages;
        question = messages?.length > 0 ? String(messages[messages.length - 1].content ?? "") : "";
      } catch {
        res.writeHead(400).end();
        return;
      }

      res.writeHead(200, {
        "content-type": "text/event-stream",
        "cache-control": "no-store",
      });
      res.flushHeaders();

      if (question.includes("quick ratio")) {
        sendEvent(res, { choices: [{ delta: { refusal: "Từ chối trả lời." } }] });
        finish(res);
      } else if (question.includes("data drift")) {
        setTimeout(() => {
          sendEvent(res, { choices: [{ delta: { content: "muộn" } }] });
          finish(res);
        }, 10_000);
      } else if (question.includes("financial distress")) {
        res.write("data: {not json\n\n");
        res.end();
      } else {
        sendEvent(res, { choices: [{ delta: { content: "The current ratio " } }] });
        sendEvent(res, { choices: [{ delta: { content: "measures " } }] });
        setTimeout(() => sendEvent(res, { choices: [{ delta: { content: "liquidity" } }] }), 20);
        setTimeout(() => finish(res), 40);
      }
    });
  })
  .listen(port, () => {
    console.log(`fake upstream listening on ${port}`);
  });
