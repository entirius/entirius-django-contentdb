# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from PIL import Image

from django_contentdb.image_manager import ImageManager


def test_resize_fill_crop_crops_a_larger_image_to_the_target_size():
    result = ImageManager.resize_fill_crop(Image.new("RGB", (200, 100), "red"), 50, 50)

    assert result.size == (50, 50)


def test_resize_fill_crop_pads_a_smaller_image_with_white():
    result = ImageManager.resize_fill_crop(Image.new("RGB", (20, 10), "red"), 40, 40)

    assert result.size == (40, 40)
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_resize_fill_crop_crops_and_pads_a_tall_narrow_image():
    result = ImageManager.resize_fill_crop(Image.new("RGB", (10, 40), "red"), 30, 20)

    assert result.size == (30, 20)
    assert result.getpixel((0, 10)) == (255, 255, 255)
    assert result.getpixel((15, 10)) == (255, 0, 0)


def test_resize_fill_crop_crops_and_pads_a_wide_short_image():
    result = ImageManager.resize_fill_crop(Image.new("RGB", (40, 10), "red"), 20, 30)

    assert result.size == (20, 30)
    assert result.getpixel((10, 0)) == (255, 255, 255)
    assert result.getpixel((10, 15)) == (255, 0, 0)
