from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
import json
from uuid import uuid4

import requests

from incluscan.config import PROMPT_TEMPLATE_PATH
from incluscan.models import ReviewFinding, ScanRunSummary, ScrapedPage, SnapshotMetadata


def build_review_prompt(content: str) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{content}}", content)


def parse_review_response(raw_text: str) -> list[ReviewFinding]:
    payload = json.loads(raw_text)
    if not isinstance(payload, list):
        raise ValueError("model response must be a JSON array")

    findings: list[ReviewFinding] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("each finding must be an object")
        if set(item) != {"original", "modified", "justification"}:
            raise ValueError("each finding must contain only original, modified, and justification")
        findings.append(ReviewFinding(**item))
    return findings


def build_request_completion(vendor_name: str, model: str, api_key: str | None = None) -> Callable[[str], tuple[str, int | None, int | None]]:
    def request_completion(prompt: str) -> tuple[str, int | None, int | None]:
        if vendor_name == "Ollama":
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            return payload["response"], None, None

        if vendor_name == "OpenAI":
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return payload["choices"][0]["message"]["content"], usage.get("prompt_tokens"), usage.get("completion_tokens")

        if vendor_name == "Anthropic":
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                json={"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return payload["content"][0]["text"], usage.get("input_tokens"), usage.get("output_tokens")

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usageMetadata", {})
        return payload["candidates"][0]["content"]["parts"][0]["text"], usage.get("promptTokenCount"), usage.get("candidatesTokenCount")

    return request_completion


def scan_snapshot(
    snapshot: SnapshotMetadata,
    pages: list[ScrapedPage],
    request_completion: Callable[[str], tuple[str, int | None, int | None]],
    vendor_name: str,
    model: str,
) -> tuple[ScanRunSummary, dict[str, list[ReviewFinding]]]:
    started_at = datetime.now(timezone.utc).isoformat()
    findings_by_url: dict[str, list[ReviewFinding]] = {}
    input_tokens = 0
    output_tokens = 0
    saw_tokens = False

    for page in pages:
        prompt = build_review_prompt(page.text)
        raw_response, page_input_tokens, page_output_tokens = request_completion(prompt)
        findings_by_url[page.url] = parse_review_response(raw_response)
        if page_input_tokens is not None:
            input_tokens += page_input_tokens
            saw_tokens = True
        if page_output_tokens is not None:
            output_tokens += page_output_tokens
            saw_tokens = True

    finished_at = datetime.now(timezone.utc).isoformat()
    run = ScanRunSummary(
        scan_id=f"scan-{uuid4().hex[:8]}",
        snapshot_id=snapshot.snapshot_id,
        base_url=snapshot.base_url,
        snapshot_fetched_at=snapshot.fetched_at,
        vendor=vendor_name,
        model=model,
        started_at=started_at,
        finished_at=finished_at,
        input_tokens=input_tokens if saw_tokens else None,
        output_tokens=output_tokens if saw_tokens else None,
    )
    return run, findings_by_url
