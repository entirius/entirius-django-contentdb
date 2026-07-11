# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from enum import Enum

from PIL import Image, ImageOps
from PIL.Image import Image as ImageClass


class ImageExtension(str, Enum):
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    GIF = ".gif"
    SVG = ".svg"
    WEBP = ".webp"


class ImageManager:
    @staticmethod
    def check_or_create_dir(path):
        if os.path.isdir(path):
            return True
        else:
            os.makedirs(path)
            return False

    @staticmethod
    def is_image(filename: str) -> bool:
        valid_extensions = []
        for elem in ImageExtension:
            valid_extensions.append(elem.value)

        result = filename.lower().endswith(tuple(*valid_extensions))
        return result

    @staticmethod
    def get_extension(filename: str):
        ext = os.path.splitext(filename)[1]
        return ext

    @staticmethod
    def set_extension(filename: str, ext: "ImageExtension") -> str:
        base = os.path.splitext(filename)[0]
        return f"{base}.{ext.value}"

    @staticmethod
    def open_image(path: str) -> ImageClass:
        result = Image.open(path)
        return result

    @staticmethod
    def save_image(image: ImageClass, path, quality=70, optimize=True) -> None:
        image.save(path, quality=quality, optimize=optimize)

    @staticmethod
    def delete_image(path: str) -> None:
        os.remove(path)

    @staticmethod
    def remove_transparency(image: ImageClass, fill_with: str = "WHITE") -> ImageClass:
        if image.mode == "RGBA":
            new_image = Image.new("RGBA", image.size, fill_with)
            new_image.paste(image, (0, 0), image)
            result = new_image
        else:
            result = image.convert("RGB")

        return result

    @staticmethod
    def resize_fill_crop(image: ImageClass, out_x: int, out_y: int) -> ImageClass:
        resize_option = Image.ANTIALIAS

        if image.width > out_x and image.height > out_y:
            result = ImageOps.fit(image, (out_x, out_y), resize_option, centering=(0.5, 0.5))
        elif image.width < out_x and image.height > out_y:
            result = ImageOps.fit(image, (image.width, out_y), resize_option, centering=(0.5, 0.5)).pad(
                image, (out_x, out_y), resize_option, color=(255, 255, 255), centering=(0.5, 0.5)
            )
        elif image.width > out_x and image.height < out_y:
            result = ImageOps.fit(image, (out_x, image.height), resize_option, centering=(0.5, 0.5)).pad(
                image, (out_x, out_y), resize_option, color=(255, 255, 255), centering=(0.5, 0.5)
            )
        else:
            result = ImageOps.pad(image, (out_x, out_y), resize_option, color=(255, 255, 255), centering=(0.5, 0.5))

        return result
