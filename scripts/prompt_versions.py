"""Quản lý prompt `day13-chat` trên project Langfuse cá nhân.

Các lệnh:
  setup     tạo v1 (labels baseline, production) và v2 (label candidate) nếu chưa có
  status    in version và labels hiện tại
  promote   chuyển label production sang version candidate
  rollback  chuyển label production về version baseline

Đọc key từ `.env`; không in key ra màn hình.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from app.cli import configure_utf8_stdio
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE

PROMPT_V1 = DEFAULT_PROMPT_TEMPLATE
PROMPT_V2 = DEFAULT_PROMPT_TEMPLATE + "\nAnswer in at most 3 short bullet points."


def _prompt_name() -> str:
    return os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def _version_with_label(client, label: str) -> int | None:
    try:
        prompt = client.get_prompt(_prompt_name(), label=label, cache_ttl_seconds=0, max_retries=0)
    except Exception:
        return None
    return prompt.version


def status(client) -> None:
    for label in ("production", "baseline", "candidate", "latest"):
        version = _version_with_label(client, label)
        print(f"{_prompt_name()} label={label:<10} version={version}")


def setup(client) -> None:
    name = _prompt_name()
    if _version_with_label(client, "baseline") is None:
        v1 = client.create_prompt(
            name=name,
            prompt=PROMPT_V1,
            labels=["baseline", "production"],
            type="text",
            commit_message="v1 baseline: format mặc định của lab",
        )
        print(f"Đã tạo v{v1.version} với labels baseline, production")
    if _version_with_label(client, "candidate") is None:
        v2 = client.create_prompt(
            name=name,
            prompt=PROMPT_V2,
            labels=["candidate"],
            type="text",
            commit_message="v2 candidate: giới hạn câu trả lời tối đa 3 bullet",
        )
        print(f"Đã tạo v{v2.version} với label candidate")
    status(client)


def move_production(client, source_label: str) -> None:
    version = _version_with_label(client, source_label)
    if version is None:
        raise SystemExit(f"Không tìm thấy version có label {source_label}; chạy `setup` trước.")
    labels = [source_label, "production"]
    client.update_prompt(name=_prompt_name(), version=version, new_labels=labels)
    print(f"production -> v{version} ({source_label})")
    status(client)


def main() -> None:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["setup", "status", "promote", "rollback"])
    args = parser.parse_args()

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        raise SystemExit("Thiếu LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY trong .env")

    from langfuse import get_client

    client = get_client()
    if args.command == "setup":
        setup(client)
    elif args.command == "status":
        status(client)
    elif args.command == "promote":
        move_production(client, "candidate")
    else:
        move_production(client, "baseline")


if __name__ == "__main__":
    main()
