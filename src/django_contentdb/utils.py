# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import hashlib
import io
import logging
import os
import tempfile
from math import ceil

import image_transformations
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db.models.fields.files import ImageField, ImageFieldFile
from PIL import Image
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

from django_contentdb.settings import CONTENTDB_IMAGE_MAX_WIDTH

logger = logging.getLogger(__name__)


def standard_exception_handler(exc, context):

    handled = exception_handler(exc, context)

    if handled is not None:
        code = handled.status_code
        if code == 400:
            status = "BAD_REQUEST"
        elif code == 401:
            status = "UNAUTHORIZED"
        elif code == 403:
            status = "FORBIDDEN"
        elif code == 404:
            status = "NOT_FOUND"
        else:
            status = "ERR"

        response = Response(
            data={"meta": {"status": status, "status_code": code, "message": exc.get_codes()}, "data": handled.data},
            status=handled.status_code,
            exception=True,
        )
    else:
        logger.exception(exc)
        status = "UNHANDLED EXCEPTION"
        response = Response(
            data={
                "meta": {"status": "ERR", "status_code": 500, "message": "Server Error"},
                "data": "Unhandled exception",
            },
            status=500,
            exception=True,
        )

    logger.error(f"ERROR: {status}\nEXCEPTION: {exc}\nCONTEXT: {context}")

    return response


class StandardPagination(PageNumberPagination):
    page_query_param = "page"
    page_size = 6
    page_size_query_param = "limit"
    max_page_size = 100

    def get_paginated_response(self, data):
        meta = {"status": "OK", "message": ""}

        return Response(
            {
                "meta": meta,
                "data": data,
                "pagination": {
                    "page": self.page.number,
                    "limit": self.get_page_size(self.request),
                    "pages": ceil(self.page.paginator.count / self.get_page_size(self.request)),
                    "records": self.page.paginator.count,
                },
            }
        )


class HashedImageFieldFile(ImageFieldFile):
    def _compute_hash(self, content):
        hash_func = hashlib.sha256()
        chunk_size = getattr(content, "DEFAULT_CHUNK_SIZE", File.DEFAULT_CHUNK_SIZE)
        # WARNING Make sure whole file is being read
        for chunk in iter(lambda: content.read(chunk_size), b""):
            hash_func.update(chunk)
        return hash_func.hexdigest()

    def _get_content_name(self, name, content):
        """
        This method computes name based on content.
        It needs original filename in order to keep the extension the same.
        It disregards filename and directory structure present in the name parameter.
        """
        # If no name is provided use content filename to get file extension
        if name is None:
            name = content.name

        # Get file extension
        file_ext = os.path.splitext(name)[1]

        # Compute hash base on content
        # Ensure stream is at start
        try:
            content.seek(0)
        except Exception:
            pass
        file_hash = self._compute_hash(content=content)

        # Get final directory structure
        final_dir_name = os.path.join(file_hash[0:2], file_hash[2:4])

        # Get final file name
        final_file_name = "".join([file_hash[4:], file_ext])

        # file_ext includes the dot.
        result = os.path.join(final_dir_name, final_file_name)
        return result

    def _maybe_resize_image(self, name: str, content: File) -> File:
        """
        Optionally downscale the image to a maximum width defined in settings, keeping aspect ratio.
        Only reduces size; never upscales. Uses image_transformations if available.
        Returns a new File-like object if resized, otherwise returns the original content (rewound).
        """
        max_width = CONTENTDB_IMAGE_MAX_WIDTH

        # If max_width is falsy or <= 0, skip processing
        if not max_width or max_width <= 0:
            try:
                content.seek(0)
            except Exception:
                pass
            return content

        # Remember original name/extension to preserve format
        orig_name = name or getattr(content, "name", None) or "upload"
        orig_ext = os.path.splitext(orig_name)[1].lower()

        # Read content into bytes for safe re-use
        try:
            content.seek(0)
        except Exception:
            pass
        data = content.read()
        if not data:
            # Empty file; nothing to do
            try:
                content.seek(0)
            except Exception:
                pass
            return content

        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            # Ensure extension matches actual image format (preserve WEBP/PNG/JPEG, etc.)
            try:
                fmt = (img.format or "").upper()
            except Exception:
                fmt = ""
            ext_map = {
                "JPEG": ".jpg",
                "JPG": ".jpg",
                "PNG": ".png",
                "WEBP": ".webp",
                "GIF": ".gif",
                "BMP": ".bmp",
                "TIFF": ".tiff",
                "TIF": ".tif",
            }
            if not orig_ext:
                orig_ext = ext_map.get(fmt, ".png")
            else:
                wanted_ext = ext_map.get(fmt)
                if wanted_ext and wanted_ext != orig_ext:
                    # Align extension with real format to avoid unintended conversion
                    orig_ext = wanted_ext
        except Exception:
            # Not an image or unreadable
            try:
                content.seek(0)
            except Exception:
                pass
            return content

        width, height = img.size
        if width <= 0 or height <= 0:
            try:
                content.seek(0)
            except Exception:
                pass
            return content

        # Only downscale if current width exceeds the limit
        if width <= max_width:
            # Rewind original content for subsequent reads
            try:
                content.seek(0)
            except Exception:
                pass
            return content

        # Compute target size preserving aspect ratio
        target_width = max_width
        aspect = height / float(width)
        target_height = max(1, int(round(target_width * aspect)))

        # Prefer using image_transformations (correct usage with file paths)
        try:
            has_alpha = ("A" in img.getbands()) or bool(getattr(img, "info", {}).get("transparency"))

            # Prepare temp files with proper extension so PIL infers format
            src_fd, src_path = tempfile.mkstemp(suffix=orig_ext or ".png")
            out_fd, out_path = tempfile.mkstemp(suffix=orig_ext or ".png")
            os.close(src_fd)
            os.close(out_fd)
            try:
                with open(src_path, "wb") as _f:
                    _f.write(data)
                # Use library: src_path, out_path, out_x, out_y, fill_color, is_transparent, quality
                image_transformations.resize_ratio_safe(
                    src_path, out_path, target_width, target_height, is_transparent=has_alpha, quality=85
                )
                # Read processed bytes and return early
                with open(out_path, "rb") as _f:
                    processed = _f.read()
                if processed:
                    new_name = os.path.splitext(orig_name)[0] + orig_ext
                    new_content = ContentFile(processed)
                    new_content.name = new_name
                    try:
                        new_content.seek(0)
                    except Exception:
                        pass
                    # Cleanup temp files
                    try:
                        os.remove(src_path)
                        os.remove(out_path)
                    except Exception:
                        pass
                    return new_content
            finally:
                try:
                    if os.path.exists(src_path):
                        os.remove(src_path)
                except Exception:
                    pass
                try:
                    if os.path.exists(out_path):
                        os.remove(out_path)
                except Exception:
                    pass
        except Exception:
            pass

            # Fallback to Pillow resize if library call failed
            try:
                resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                transformed_img = img.resize((target_width, target_height), resample=resample)
            except Exception:
                # On failure, return original content
                try:
                    content.seek(0)
                except Exception:
                    pass
                return content

        # Determine output format
        format_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".webp": "WEBP",
            ".gif": "GIF",
            ".bmp": "BMP",
            ".tif": "TIFF",
            ".tiff": "TIFF",
        }
        out_format = format_map.get(orig_ext, img.format or "PNG")

        out = io.BytesIO()
        save_kwargs = {}
        # Apply reasonable compression defaults
        if out_format in ("JPEG", "WEBP"):
            save_kwargs.update({"quality": 85})
            # progressive only for JPEG
            if out_format == "JPEG":
                save_kwargs.update({"optimize": True, "progressive": True})
        elif out_format == "PNG":
            save_kwargs.update({"optimize": True})

        try:
            transformed_img.save(out, format=out_format, **save_kwargs)
        except Exception:
            # If saving with format fails, try PNG as safe default
            out = io.BytesIO()
            try:
                transformed_img.save(out, format="PNG")
                out_format = "PNG"
                orig_ext = ".png"
            except Exception:
                # Give up and return original
                try:
                    content.seek(0)
                except Exception:
                    pass
                return content

        out.seek(0)

        # Create a Django File-like object preserving original name extension
        new_name = os.path.splitext(orig_name)[0] + orig_ext
        new_content = ContentFile(out.read())
        new_content.name = new_name
        try:
            new_content.seek(0)
        except Exception:
            pass
        return new_content

    def save(self, name: str, content: File, save: bool = ...) -> None:
        """
        This method disregards the name parameter.
        This method gets called when you call instance.image.save(filename, file).
        Computes checksum for content and uses it to construct the final path to which the file will be saved.
        Additionally, downscales and compresses images to a maximum width configured in settings.
        """
        # Optionally resize before hashing and saving
        try:
            processed_content = self._maybe_resize_image(name, content)
        except Exception as e:
            logger.warning(f"Image resize failed, saving original. Error: {e}")
            processed_content = content

        # Compute name by hash of processed content
        name_from_hash = self._get_content_name(name, processed_content)

        # Ensure stream at start for actual save
        try:
            processed_content.seek(0)
        except Exception:
            pass

        return super().save(name_from_hash, processed_content, save)


class HashedImageField(ImageField):
    # Change attr_class so save method can be overriden
    attr_class = HashedImageFieldFile


class UniqueFileSystemStorage(FileSystemStorage):
    def get_alternative_name(self, file_root, file_ext):
        # Allow saving a duplicate by delegating to Django's default alternative name generation.
        # This will append a unique suffix to the filename instead of raising an error.
        return super().get_alternative_name(file_root, file_ext)
