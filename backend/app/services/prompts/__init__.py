"""Prompt 加载与占位符替换。"""
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def load(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def render(name: str, **kwargs: str) -> str:
    text = load(name)
    for k, v in kwargs.items():
        text = text.replace("{{" + k + "}}", v)
    return text
