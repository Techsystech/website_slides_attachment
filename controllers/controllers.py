import base64
import json
import logging
import mimetypes
import mmap
import os
import shutil
import tempfile

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.utils import secure_filename

_logger = logging.getLogger(__name__)

# Chunk size for streaming downloads
STREAM_CHUNK_SIZE = 512 * 1024


class UploadController(http.Controller):

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload),
            headers=[("Content-Type", "application/json")],
            status=status,
        )

    def _check_slide_access(self, slide_id, operation="read"):
        slide = request.env["slide.slide"].browse(int(slide_id or 0)).exists()
        if not slide:
            raise NotFound()
        try:
            slide.check_access(operation)
        except (AccessError, MissingError):
            raise Forbidden()
        return slide

    def _attachment_from_token(self, token):
        attachment_id = request.env["slide.slide"]._local_video_attachment_id_from_token(token)
        if not attachment_id:
            return request.env["ir.attachment"]
        return request.env["ir.attachment"].sudo().browse(attachment_id).exists()

    def _form_json_value(self, post, key, default=None):
        value = post.get(key)
        if not value:
            return default
        if not isinstance(value, str):
            return value
        return json.loads(value)

    def _form_truthy(self, post, key):
        return str(post.get(key, "")).lower() in ("1", "true", "yes", "on")

    # ------------------------------------------------------------------
    # Streaming upload — memory-mapped to bypass base64 and avoid
    # loading multi-hundred-megabyte files into Python heap.
    # ------------------------------------------------------------------

    def _create_streaming_attachment(self, slide, file_storage):
        """Create an ir.attachment from a streamed upload via memory-mapped file.

        Werkzeug already stores large uploads in a temp file on disk.
        We memory-map that temp file and pass the mmap object as ``raw``.
        Odoo's ``_get_datas_related_values`` reads from the mmap to compute
        the SHA-1 and write to the filestore, but the OS pages data in/out
        instead of loading the whole file into RAM.
        """
        filename = secure_filename(file_storage.filename or slide.name or "local-video") or "local-video"
        mimetype = file_storage.mimetype or mimetypes.guess_type(filename)[0] or "video/mp4"

        # Werkzeug's FileStorage may already be backed by a temp file.
        # Save to our own temp path so we can mmap it safely.
        # NOTE: we cannot use file_storage.save() because Odoo monkey-patches
        # FileStorage.save to call copyfileobj(self.stream, dst) without
        # converting a string dst to an open file handle.
        temp_path = tempfile.mktemp()
        with open(temp_path, "wb") as dst:
            shutil.copyfileobj(file_storage.stream, dst, STREAM_CHUNK_SIZE)

        try:
            with open(temp_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    attachment = request.env["ir.attachment"].sudo().create({
                        "name": filename,
                        "type": "binary",
                        "raw": mm,
                        "mimetype": mimetype,
                        "res_model": "slide.slide",
                        "res_id": slide.id,
                    })
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        return attachment

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @http.route("/website_slides_attachment/upload", type="http", auth="user", methods=["POST"], max_content_length=None)
    def upload_file(self, **kwargs):
        file_storage = request.httprequest.files.get("file")
        if not file_storage or not file_storage.filename:
            return self._json_response({"error": "Missing upload file"}, status=400)

        slide = self._check_slide_access(request.httprequest.form.get("res_id"), operation="write")
        attachment = self._create_streaming_attachment(slide, file_storage)

        token = slide._local_video_attachment_token(attachment.id)
        slide.sudo().write({
            "is_local_video": True,
            "video_binary_content": token,
        })
        return self._json_response({
            "id": attachment.id,
            "name": attachment.name,
            "mimetype": attachment.mimetype,
            "token": token,
        })

    def _create_local_video_attachment(self, slide, file_storage):
        attachment = self._create_streaming_attachment(slide, file_storage)
        slide.sudo().write({
            "is_local_video": True,
            "video_binary_content": slide._local_video_attachment_token(attachment.id),
        })
        return attachment

    @http.route(
        "/website_slides_attachment/add_local_video_slide",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        max_content_length=None,
    )
    def add_local_video_slide(self, **post):
        file_storage = request.httprequest.files.get("local_video_file")
        if not file_storage or not file_storage.filename:
            return self._json_response({"error": _("Missing upload file")}, status=400)
        try:
            channel = request.env["slide.channel"].browse(int(post.get("channel_id") or 0)).exists()
            if not channel or not channel.can_upload:
                return self._json_response({"error": _("You cannot upload on this channel.")}, status=403)
            values = {
                "channel_id": channel.id,
                "name": post.get("name") or secure_filename(post.get("file_name") or "Local Video"),
                "slide_category": "video",
                "is_local_video": True,
                "is_published": self._form_truthy(post, "is_published"),
                "user_id": request.env.uid,
            }
            if post.get("duration"):
                values["completion_time"] = int(post["duration"]) / 60
            tag_ids = self._form_json_value(post, "tag_ids")
            if tag_ids:
                values["tag_ids"] = tag_ids
            category_value = self._form_json_value(post, "category_id")
            if category_value:
                category_id = category_value[0]
                if category_id == 0:
                    category = request.env["slide.slide"].sudo().create({
                        "channel_id": channel.id,
                        "name": category_value[1]["name"],
                        "is_category": True,
                        "is_published": True,
                    })
                    values["sequence"] = category.sequence + 1
                else:
                    category = request.env["slide.slide"].browse(category_id)
                    values["sequence"] = category.sequence + 1
                    values["category_id"] = category.id
            else:
                category = False
            slide = request.env["slide.slide"].sudo().create(values)
            self._create_local_video_attachment(slide, file_storage)
            channel._resequence_slides(slide, force_category=category)
            redirect_url = "/slides/%s" % request.env["ir.http"]._slug(channel) if channel.channel_type == "training" else "/slides/slide/%s" % request.env["ir.http"]._slug(slide)
            return self._json_response({"url": redirect_url, "slide_id": slide.id, "category_id": slide.category_id.id})
        except UserError as e:
            _logger.error(e)
            return self._json_response({"error": e.args[0]}, status=400)
        except Exception as e:
            _logger.exception("Failed creating local video slide")
            return self._json_response({"error": _("Internal server error, please try again later or contact administrator.\nHere is the error message: %s", e)}, status=500)

    @http.route("/website_slides_attachment/remove", type="http", auth="user", methods=["POST"])
    def remove_file(self, **kwargs):
        token = request.httprequest.form.get("attachment_token") or request.httprequest.form.get("file_path")
        attachment = self._attachment_from_token(token)
        if not attachment:
            return self._json_response({"removed": False, "legacy": True}, status=200)

        if attachment.res_model != "slide.slide" or not attachment.res_id:
            raise Forbidden()
        self._check_slide_access(attachment.res_id, operation="write")
        attachment.unlink()
        return self._json_response({"removed": True}, status=200)

    @http.route([
        "/website_slides_attachment/download/<int:id>",
        "/website_slides_attachment/download/<int:id>/filename=<path:file_name>",
    ], type="http", auth="user", methods=["GET"])
    def download_file(self, id=None, file_name=None, **kwargs):
        slide = self._check_slide_access(id, operation="read")
        attachment = slide._get_local_video_attachment()

        if attachment:
            filename = secure_filename(attachment.name or slide.name or "local-video") or "local-video"
            mimetype = attachment.mimetype or mimetypes.guess_type(filename)[0] or "video/mp4"
            file_path = attachment._full_path(attachment.store_fname) if attachment.store_fname else None
            if file_path and os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                data_source = file_path
                is_file = True
            else:
                # Fallback to datas (base64) if filestore path is missing
                data = base64.b64decode(attachment.datas or b"")
                file_size = len(data)
                data_source = data
                is_file = False
        else:
            legacy_path = slide._get_legacy_local_video_path()
            if not legacy_path:
                raise NotFound()
            filename = secure_filename(file_name or slide.name or legacy_path.name) or "local-video"
            mimetype = mimetypes.guess_type(str(legacy_path))[0] or "video/mp4"
            file_size = legacy_path.stat().st_size
            data_source = str(legacy_path)
            is_file = True

        range_header = request.httprequest.headers.get("Range")
        status = 200
        headers = [
            ("Content-Type", mimetype),
            ("Accept-Ranges", "bytes"),
            ("Content-Disposition", f"inline; filename=\"{filename}\""),
        ]

        if range_header and range_header.startswith("bytes="):
            range_value = range_header.split("=", 1)[1].split(",", 1)[0]
            start_s, end_s = (range_value.split("-", 1) + [""])[:2]
            range_start = int(start_s) if start_s else 0
            range_end = int(end_s) if end_s else file_size - 1
            range_start = max(0, min(range_start, file_size))
            range_end = max(range_start, min(range_end, file_size - 1))
            status = 206
            headers.extend([
                ("Content-Range", f"bytes {range_start}-{range_end}/{file_size}"),
                ("Content-Length", str(range_end - range_start + 1)),
            ])

            if is_file:
                with open(data_source, "rb") as f:
                    f.seek(range_start)
                    data = f.read(range_end - range_start + 1)
                return request.make_response(data, headers=headers, status=status)
            else:
                return request.make_response(
                    data_source[range_start:range_end + 1],
                    headers=headers,
                    status=status,
                )

        headers.append(("Content-Length", str(file_size)))

        if is_file:
            # Stream from disk in chunks to avoid loading large files into memory
            def file_stream():
                with open(data_source, "rb") as f:
                    while True:
                        chunk = f.read(STREAM_CHUNK_SIZE)
                        if not chunk:
                            break
                        yield chunk
            return request.make_response(
                file_stream(),
                headers=headers,
                status=status,
            )
        else:
            return request.make_response(data_source, headers=headers, status=status)
