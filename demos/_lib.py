"""Shared presentation helpers so every demo looks the same on camera."""

from __future__ import annotations


def banner(text: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n  {text}\n{bar}")


def rule(text: str = "") -> None:
    print(f"\n--- {text} ".ljust(72, "-") if text else "-" * 72)


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"
