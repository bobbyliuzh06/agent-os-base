#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redact：日志/产物脱敏。仅用于写盘前处理（result.json / run.log / violation.json），
不改动进程原始控制台输出。"""
import re

REDACT_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "api_key"),
    (re.compile(r"AKIA[0-9A-Z]{8,}"), "aws_key"),
    (re.compile(r"gh[opu]s?_[A-Za-z0-9]{20,}"), "github_token"),
    (re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*(?!<REDACTED)\S+"), "credential"),
]

def redact(text):
    """替换文本中的密钥样式为 <REDACTED:type>。"""
    if not isinstance(text, str):
        return text
    for pat, kind in REDACT_PATTERNS:
        text = pat.sub("<REDACTED:%s>" % kind, text)
    return text
