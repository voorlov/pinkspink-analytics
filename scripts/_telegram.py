"""Telegram Bot API helpers shared between ai_report.py and check_pagespeed.py."""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request

TELEGRAM_LIMIT = 4000


def chunk_for_telegram(text: str) -> list[str]:
    """Split text into chunks <= TELEGRAM_LIMIT chars, preferring paragraph breaks."""
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= TELEGRAM_LIMIT:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n\n", 0, TELEGRAM_LIMIT)
        if cut < TELEGRAM_LIMIT // 2:
            cut = remaining.rfind("\n", 0, TELEGRAM_LIMIT)
        if cut < 0:
            cut = TELEGRAM_LIMIT
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()
    return chunks


def send_telegram(text: str, token: str | None = None, chat_id: str | None = None) -> None:
    """POST `text` to Telegram. Reads creds from env if not given.

    Falls back to plain text if Markdown parsing fails.
    """
    token = token or os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in chunk_for_telegram(text):
        for parse_mode in ("Markdown", None):
            params = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                params["parse_mode"] = parse_mode
            data = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(url, data=data)
            try:
                urllib.request.urlopen(req, timeout=15).read()
                break
            except urllib.error.HTTPError:
                if parse_mode is None:
                    raise
                continue
