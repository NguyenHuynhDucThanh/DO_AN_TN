"""Download either an official smoke subset or the explicit full Hugging Face dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BACKEND_ROOT

DATASET_ID = "mtue29/vietnamese-medical-dataset"
FILENAME = "vietnamese-medical-dataset.json"
RAW_ROOT = BACKEND_ROOT / "data" / "rag" / "raw"


def download_subset(limit: int) -> Path:
    query = urlencode({"dataset": DATASET_ID, "config": "default", "split": "train"})
    with urlopen(f"https://datasets-server.huggingface.co/first-rows?{query}", timeout=60) as response:
        payload = json.load(response)
    rows = [item["row"] for item in payload.get("rows", [])[:limit]]
    if not rows:
        raise RuntimeError("Official dataset API returned no rows.")
    target = RAW_ROOT / "vietnamese-medical-dataset.subset.jsonl"
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return target


def download_large_subset(limit: int) -> Path:
    """Download deterministic rows [0, limit) through the official paged API."""
    rows: list[dict] = []
    page_size = 100
    for offset in range(0, limit, page_size):
        length = min(page_size, limit - offset)
        query = urlencode(
            {
                "dataset": DATASET_ID,
                "config": "default",
                "split": "train",
                "offset": offset,
                "length": length,
            }
        )
        with urlopen(f"https://datasets-server.huggingface.co/rows?{query}", timeout=120) as response:
            payload = json.load(response)
        page = [item["row"] for item in payload.get("rows", [])]
        if len(page) != length:
            raise RuntimeError(f"Official dataset API returned {len(page)} rows at offset {offset}.")
        rows.extend(page)
    target = RAW_ROOT / f"vietnamese-medical-dataset.large-{limit}.jsonl"
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return target


def download_full() -> Path:
    from huggingface_hub import hf_hub_download

    downloaded = hf_hub_download(
        repo_id=DATASET_ID,
        repo_type="dataset",
        filename=FILENAME,
        local_dir=RAW_ROOT,
    )
    return Path(downloaded)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--subset", type=int, metavar="N")
    mode.add_argument("--large-subset", type=int, metavar="N")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args()
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    if args.subset is not None:
        if not 1 <= args.subset <= 100:
            parser.error("--subset must be between 1 and 100")
        target = download_subset(args.subset)
        print(f"SUBSET_DOWNLOAD_OK path={target} rows={args.subset}")
    elif args.large_subset is not None:
        if not 100 <= args.large_subset <= 10_000:
            parser.error("--large-subset must be between 100 and 10000")
        target = download_large_subset(args.large_subset)
        print(f"LARGE_SUBSET_DOWNLOAD_OK path={target} rows={args.large_subset}")
    else:
        target = download_full()
        print(f"FULL_DOWNLOAD_OK path={target} bytes={target.stat().st_size}")


if __name__ == "__main__":
    main()
