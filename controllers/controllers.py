import base64
import json
import logging
import mimetypes

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.utils import secure_filename

_logger = logging.getLogger(__name__)


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

    @http.route("/website_slides_attachment/upload", type="http", auth="user", methods=["POST"], max_content_length=None)
    def upload_file(self, **kwargs):
        file_storage = request.httprequest.files.get("file")
        if not file_storage or not file_storage.filename:
            return self._json_response({"error": "Missing upload file"}, status=400)

        # This endpoint is intentionally limited to existing slide records. The old
        # implementation accepted arbitrary res_model/save_location input from the
        # browser, which allowed server-side path write abuse.
        slide = self._check_slide_access(request.httprequest.form.get("res_id"), operation="write")

        filename = secure_filename(file_storage.filename) or "local-video"
        mimetype = file_storage.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        attachment = request.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(file_storage.stream.read()),
            "mimetype": mimetype,
            "res_model": "slide.slide",
            "res_id": slide.id,
        })
        token = slide._local_video_attachment_token(attachment.id)
        return self._json_response({
            "id": attachment.id,
            "name": attachment.name,
            "token": token,
        })

    @http.route("/website_slides_attachment/remove", type="http", auth="user", methods=["POST"])
    def remove_file(self, **kwargs):
        token = request.httprequest.form.get("attachment_token") or request.httprequest.form.get("file_path")
        attachment = self._attachment_from_token(token)
        if not attachment:
            # Legacy filesystem paths are not deleted from a browser-provided value.
            # Clearing the slide field is handled client-side; filesystem cleanup belongs
            # in the controlled migration/admin flow.
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
            data = base64.b64decode(attachment.datas or b"")
        else:
            legacy_path = slide._get_legacy_local_video_path()
            if not legacy_path:
                raise NotFound()
            filename = secure_filename(file_name or slide.name or legacy_path.name) or "local-video"
            mimetype = mimetypes.guess_type(str(legacy_path))[0] or "video/mp4"
            data = legacy_path.read_bytes()

        file_size = len(data)
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
            data = data[range_start:range_end + 1]
            status = 206
            headers.extend([
                ("Content-Range", f"bytes {range_start}-{range_end}/{file_size}"),
                ("Content-Length", str(len(data))),
            ])
        else:
            headers.append(("Content-Length", str(file_size)))

        return request.make_response(data, headers=headers, status=status)
