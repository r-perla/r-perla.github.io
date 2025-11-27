#!/usr/bin/env python3
"""Back up and optimize images under img/new_profiles."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "img" / "new_profiles"
MAX_DIMENSION = 1600  # Max width/height in pixels
JPEG_QUALITY = 80


def ensure_source_dir():
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Source directory not found: {SOURCE_DIR}")
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"Source path is not a directory: {SOURCE_DIR}")


def create_backup_dir() -> Path:
    """Create a timestamped backup directory inside img/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT / "img" / f"new_profiles_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    return backup_dir


def back_up_images(backup_dir: Path) -> None:
    for item in SOURCE_DIR.iterdir():
        if item.is_file():
            shutil.copy2(item, backup_dir / item.name)


def optimize_image(image_path: Path, backup_dir: Path) -> tuple[int, int, bool] | None:
    suffix = image_path.suffix.lower()
    formats = {".jpg", ".jpeg", ".jpe", ".jfif"}
    before = image_path.stat().st_size

    if suffix not in formats and suffix != ".png":
        print(f"Skipping unsupported format: {image_path.name}")
        return None

    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)

        if max(img.size) > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        save_kwargs: dict[str, object] = {}

        if suffix in formats:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            save_kwargs.update(
                {
                    "format": "JPEG",
                    "quality": JPEG_QUALITY,
                    "optimize": True,
                    "progressive": True,
                }
            )
        else:
            # PNG
            if img.mode == "P" and img.palette is None:
                img = img.convert("RGBA")
            save_kwargs.update({"format": "PNG", "optimize": True})

        img.save(image_path, **save_kwargs)

    after = image_path.stat().st_size
    if after > before:
        # Keep the smaller original if optimization did not help.
        shutil.copy2(backup_dir / image_path.name, image_path)
        return before, before, True

    return before, after, False


def main():
    ensure_source_dir()
    backup_dir = create_backup_dir()
    back_up_images(backup_dir)
    print(f"Backed up original images to: {backup_dir}")

    for image_path in sorted(SOURCE_DIR.iterdir()):
        if not image_path.is_file():
            continue
        result = optimize_image(image_path, backup_dir)
        if result is None:
            continue
        before, after, reverted = result
        status = "reverted to original" if reverted else ""
        print(
            f"{image_path.name}: {before/1024:.1f} KB -> {after/1024:.1f} KB "
            f"({(after - before) / max(before, 1) * 100:.1f}%) {status}".strip()
        )


if __name__ == "__main__":
    main()
