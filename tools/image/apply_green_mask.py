#!/usr/bin/env python3
# 用途: 将图片 A 中纯 RGB #00FF00 的像素位置同步涂到目录 B 内所有同尺寸图片上。
# 用法: python tools/image/apply_green_mask.py path/to/A.png path/to/B
# 递归处理子目录: python tools/image/apply_green_mask.py path/to/A.png path/to/B --recursive
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    print(
        "Pillow is required. Install it with: python -m pip install Pillow",
        file=sys.stderr,
    )
    sys.exit(1)


GREEN = (0, 255, 0)
IMAGE_EXTENSIONS = {
    ".bmp",
    ".dib",
    ".gif",
    ".jfif",
    ".jpe",
    ".jpeg",
    ".jpg",
    ".pbm",
    ".pgm",
    ".png",
    ".ppm",
    ".tif",
    ".tiff",
    ".webp",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Apply the pure RGB #00FF00 pixels from one mask image to every "
            "same-sized image in a directory."
        )
    )
    parser.add_argument(
        "mask_image", type=Path, help="Image A containing #00FF00 mask pixels"
    )
    parser.add_argument(
        "target_dir", type=Path, help="Directory B containing images to update"
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process images in target_dir recursively",
    )
    return parser.parse_args()


def is_same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve().samefile(right.resolve())
    except FileNotFoundError:
        return False


def iter_images(directory: Path, recursive: bool):
    pattern = "**/*" if recursive else "*"
    for path in directory.glob(pattern):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def build_green_mask(mask_image: Image.Image) -> list[tuple[int, int]]:
    rgb_mask_image = mask_image.convert("RGB")
    pixels = rgb_mask_image.load()
    width, height = rgb_mask_image.size
    return [
        (x, y) for y in range(height) for x in range(width) if pixels[x, y] == GREEN
    ]


def apply_mask(
    image_path: Path,
    green_pixels: list[tuple[int, int]],
    expected_size: tuple[int, int],
) -> bool:
    with Image.open(image_path) as image:
        if image.size != expected_size:
            return False

        original_mode = image.mode
        rgba_image = image.convert("RGBA")
        pixels = rgba_image.load()
        for x, y in green_pixels:
            pixels[x, y] = (*GREEN, pixels[x, y][3])
        output_image = (
            rgba_image if original_mode == "RGBA" else rgba_image.convert(original_mode)
        )
        output_image.save(image_path)
        return True


def main():
    args = parse_args()
    mask_path = args.mask_image
    target_dir = args.target_dir

    if not mask_path.is_file():
        print(f"Mask image does not exist: {mask_path}", file=sys.stderr)
        return 2
    if not target_dir.is_dir():
        print(f"Target directory does not exist: {target_dir}", file=sys.stderr)
        return 2

    try:
        with Image.open(mask_path) as mask_image:
            expected_size = mask_image.size
            green_pixels = build_green_mask(mask_image)
    except UnidentifiedImageError:
        print(f"Mask image is not a supported image file: {mask_path}", file=sys.stderr)
        return 2

    updated = 0
    skipped_self = 0
    skipped_size = 0
    skipped_invalid = 0

    for image_path in iter_images(target_dir, args.recursive):
        if is_same_file(mask_path, image_path):
            skipped_self += 1
            continue

        try:
            if apply_mask(image_path, green_pixels, expected_size):
                updated += 1
            else:
                skipped_size += 1
        except UnidentifiedImageError:
            skipped_invalid += 1

    print(
        f"Updated: {updated}, skipped self: {skipped_self}, "
        f"skipped size mismatch: {skipped_size}, skipped invalid: {skipped_invalid}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
