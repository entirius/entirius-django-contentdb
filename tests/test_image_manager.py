# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
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


@pytest.mark.parametrize("size", [(30, 40), (60, 20)])
def test_resize_fill_crop_crops_when_one_side_equals_the_target(size):
    result = ImageManager.resize_fill_crop(Image.new("RGB", size, "red"), 30, 20)

    assert result.size == (30, 20)
    assert result.getpixel((0, 0)) == (255, 0, 0)


@pytest.mark.parametrize("mode", ["1", "L", "LA", "I", "I;16", "F", "P", "PA", "CMYK", "YCbCr", "HSV"])
def test_resize_fill_crop_pads_every_mode_with_white(mode):
    result = ImageManager.resize_fill_crop(Image.new(mode, (10, 40)), 30, 20)

    assert result.size == (30, 20)
    assert result.convert("RGB").getpixel((0, 0)) == (255, 255, 255)
