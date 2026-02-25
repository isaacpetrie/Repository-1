"""Vision-based extraction via OpenAI Responses API."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

from openai import OpenAI

PROMPT = """
Extract the main textual content from these webpage screenshots.
Return strict JSON with keys:
- text_markdown (string)
- tables_markdown (string)
- confidence (number 0..1)
- warnings (array of strings)
- missing_notes (string)
Focus on clean markdown. Include warnings for tiny/blurred text.
""".strip()


class VisionExtractor:
    """Wrapper around OpenAI Responses API for screenshot OCR+understanding."""

    def __init__(self, api_key: str | None, model: str = "gpt-4.1-mini") -> None:
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model

    def available(self) -> bool:
        return self.client is not None

    def extract(self, screenshot_paths: list[str]) -> dict:
        """Extract markdown text and table data from screenshots."""
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is required for vision extraction")

        content = [{"type": "input_text", "text": PROMPT}]
        for path in screenshot_paths:
            b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{b64}",
                }
            )

        resp = self.client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": content}],
            max_output_tokens=1800,
        )
        raw = resp.output_text
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.S)
            if not m:
                raise RuntimeError("Vision model returned non-JSON payload")
            return json.loads(m.group(0))
