"""Model-server benchmark harness — TTFT, inter-token latency, throughput, memory.

Drives ``src/llm/model_server.py``'s OpenAI-compatible request builder against
a running ``InferenceService`` (streaming ``/v1/chat/completions``) and
produces a comparable before/after table across the two frozen
``ModelServerConfig`` quantization variants. The prompt set and concurrency
must stay identical between the baseline and optimized runs, or the
comparison is not meaningful.
"""

from __future__ import annotations

import dataclasses
import json
import statistics
import time
import urllib.request
from collections.abc import Iterable

from src.llm.model_server import build_chat_completion_request

DEFAULT_PROMPTS: list[str] = [
    "Summarize the concept of financial distress in two sentences.",
    "List three early warning indicators of company default risk.",
]


@dataclasses.dataclass
class BenchmarkResult:
    """One prompt's measured latency/throughput/memory for one config."""

    config_label: str
    ttft_seconds: float
    inter_token_latency_seconds: float
    throughput_tokens_per_second: float
    peak_rss_mb: float
    prompt: str
    concurrency: int


def run_streaming_completion(
    base_url: str, prompt: str, *, max_tokens: int = 64, timeout: float = 120.0
) -> tuple[float, float, int]:
    """Stream one completion; return ``(ttft_seconds, total_seconds, token_count)``."""
    payload = build_chat_completion_request(
        [{"role": "user", "content": prompt}], max_tokens=max_tokens, stream=True
    )
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    ttft: float | None = None
    token_count = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for line in response:
            stripped = line.strip()
            if not stripped or stripped == b"data: [DONE]":
                continue
            if ttft is None:
                ttft = time.perf_counter() - started
            token_count += 1
    total = time.perf_counter() - started
    return (ttft or total), total, token_count


def read_peak_rss_mb(pid_status_path: str = "/proc/self/status") -> float:
    """Read ``VmHWM`` (peak resident set size) in MiB from a ``/proc/<pid>/status``-shaped file."""
    try:
        with open(pid_status_path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmHWM:"):
                    kilobytes = int(line.split()[1])
                    return round(kilobytes / 1024, 2)
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def benchmark_model_server(
    base_url: str,
    config_label: str,
    *,
    prompts: Iterable[str] = DEFAULT_PROMPTS,
    concurrency: int = 1,
    max_tokens: int = 64,
    rss_path: str = "/proc/self/status",
) -> list[BenchmarkResult]:
    """Run the frozen prompt set once per prompt at a fixed concurrency."""
    results: list[BenchmarkResult] = []
    for prompt in prompts:
        ttft, total, token_count = run_streaming_completion(base_url, prompt, max_tokens=max_tokens)
        inter_token = (total - ttft) / max(token_count - 1, 1)
        throughput = token_count / total if total > 0 else 0.0
        results.append(
            BenchmarkResult(
                config_label=config_label,
                ttft_seconds=round(ttft, 4),
                inter_token_latency_seconds=round(inter_token, 4),
                throughput_tokens_per_second=round(throughput, 2),
                peak_rss_mb=read_peak_rss_mb(rss_path),
                prompt=prompt,
                concurrency=concurrency,
            )
        )
    return results


def summarize(results: list[BenchmarkResult]) -> dict[str, float]:
    """Mean TTFT/inter-token/throughput and peak memory across a result set."""
    return {
        "mean_ttft_seconds": round(statistics.fmean(r.ttft_seconds for r in results), 4),
        "mean_inter_token_latency_seconds": round(
            statistics.fmean(r.inter_token_latency_seconds for r in results), 4
        ),
        "mean_throughput_tokens_per_second": round(
            statistics.fmean(r.throughput_tokens_per_second for r in results), 2
        ),
        "peak_rss_mb": max(r.peak_rss_mb for r in results),
    }


def render_before_after_table(
    baseline: list[BenchmarkResult], optimized: list[BenchmarkResult]
) -> str:
    """Render a Markdown table comparing baseline vs. optimized summaries."""
    base_summary = summarize(baseline)
    opt_summary = summarize(optimized)
    header = "| Metric | Baseline | Optimized |\n|---|---:|---:|\n"
    rows = "\n".join(
        f"| {key} | {base_summary[key]} | {opt_summary[key]} |" for key in base_summary
    )
    return header + rows
