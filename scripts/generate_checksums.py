#!/usr/bin/env python3
"""Generate SHA256 checksums for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterable


CHUNK_SIZE = 1024 * 1024


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(inputs: Iterable[Path], output_file: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []

    for item in inputs:
        if not item.exists():
            raise FileNotFoundError(f"Input path does not exist: {item}")

        if item.is_file():
            resolved = item.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(item)
            continue

        for child in sorted(item.rglob("*")):
            if not child.is_file():
                continue
            resolved = child.resolve()
            if resolved in seen or resolved == output_file.resolve():
                continue
            seen.add(resolved)
            files.append(child)

    files = [path for path in files if path.resolve() != output_file.resolve()]
    files.sort(key=lambda value: value.as_posix())
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SHA256 checksums for files or directories."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Files and/or directories to include in checksum generation.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="checksums.txt",
        help="Output file path (default: checksums.txt).",
    )
    parser.add_argument(
        "--relative-to",
        default=".",
        help="Base directory used for file names in output (default: current directory).",
    )
    args = parser.parse_args()

    output_file = Path(args.output).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    relative_root = Path(args.relative_to).resolve()
    input_paths = [Path(entry) for entry in args.inputs]
    files = collect_files(input_paths, output_file)

    if not files:
        raise RuntimeError("No files found to hash.")

    lines: list[str] = []
    for path in files:
        checksum = file_sha256(path)
        try:
            display_path = path.resolve().relative_to(relative_root).as_posix()
        except ValueError:
            display_path = path.resolve().as_posix()
        lines.append(f"{checksum}  {display_path}")

    output_file.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"Wrote {len(lines)} SHA256 entries to {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
