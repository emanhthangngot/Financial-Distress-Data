/**
 * Fixture-mode fake inference upstream, e2e-only.
 *
 * The assistant stream route points DISTRESSLENS_INFERENCE_URL at this server
 * so the evidence run can prove streaming, timeout, refusal and malformed
 * handling deterministically — without any real model, and without the test
 * suite ever importing this file into `src/`.
 *
 * Behaviour is selected by the last user message, so one server covers every
 * branch:
 *   - "từ chối" -> a refusal chunk, the route translates it to policy_blocked
 *   - "chậm"    -> a delay past the app's ASSISTANT_TIMEOUT_MS, then a token
 *   - "lỗi"     -> broken JSON, the route emits a MALFORMED_RESPONSE error
 *   - anything else -> a canned token stream then finish
 */
"use strict";

import http from "node:http";

const port = Number(process.env.FAKE_UPSTREAM_PORT ?? 3322);

function sendEvent(res, chunk) {
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}

function finish(res) {
  sendEvent(res, { choices: [{ delta: {}, finish_reason: "stop" }] });
  res.end();
}

http
  .createServer((req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("ok");
      return;
    }

    if (req.method !== "POST") {
      res.writeHead(405, { "content-type": "text/plain" });
      res.end("method not allowed");
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
        const messages = parsed.messages;
        question = messages?.length > 0 ? String(messages[messages.length - 1].content ?? "") : "";
      } catch {
        // A malformed body is the route's problem, not ours.
      }

      res.writeHead(200, {
        "content-type": "text/event-stream",
        "cache-control": "no-store",
      });
      res.flushHeaders();

      if (question.includes("từ chối")) {
        sendEvent(res, { choices: [{ delta: { refusal: "Từ chối trả lời." } }] });
        finish(res);
      } else if (question.includes("chậm")) {
        setTimeout(() => {
          sendEvent(res, { choices: [{ delta: { content: "muộn" } }] });
          finish(res);
        }, 10_000);
      } else if (question.includes("lỗi")) {
        res.write("data: {not json\n\n");
        res.end();
      } else {
        sendEvent(res, { choices: [{ delta: { content: "NVL " } }] });
        sendEvent(res, { choices: [{ delta: { content: "rủi ro " } }] });
        setTimeout(() => sendEvent(res, { choices: [{ delta: { content: "thanh khoản" } }] }), 20);
        setTimeout(() => finish(res), 40);
      }
    });
  })
  .listen(port, () => {
    console.log(`fake upstream listening on ${port}`);
  });
