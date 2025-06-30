import logging
from odoo import http
from odoo.http import request
from werkzeug.utils import wrap_file
import base64, os

_logger = logging.getLogger(__name__)

class UploadController(http.Controller):

    @http.route('/website_slides_attachment/upload', type='http', auth='user', csrf=False, max_content_length=None)
    def upload_file(self, **kwargs):
        file = request.httprequest.files.get('file')
        
        print('file is: ', file)
        filename = file.filename
        filename =  filename.replace(' ', '_')  # Replace spaces with underscores for the filename
        full_path = request.httprequest.form.get('save_location') + request.httprequest.form.get('res_model') + '_' + request.httprequest.form.get('time_stamp') + '_' + filename
        os.makedirs(os.path.dirname(full_path), exist_ok=True)  # Ensure the directory exists.
        with open(full_path, 'wb') as f:
            while True:
                chunk = file.stream.read(8192)
                if not chunk:
                    break
                f.write(chunk)

        # Return a success response
        return request.make_response("Upload successful", status=200)

    @http.route('/website_slides_attachment/remove', type='http', auth='user', csrf=False)
    def remove_file(self, **kwargs):
        file_path = request.httprequest.form.get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return request.make_response("File removed successfully", status=200)
        else:
            return request.make_response("File not found", status=404)

    @http.route('/website_slides_attachment/download/<int:id>/filename=<file_name>', type='http', auth='user', csrf=False)
    def download_file(self, id=None, file_name=None, **kwargs):
        slide = request.env['slide.slide'].search([('id', '=', id)])
        file_path = slide.video_binary_content
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            file_stream = open(file_path, 'rb')

            range_header = request.httprequest.headers.get('Range')
            if range_header:
                # Parse the Range header
                range_value = range_header.strip().lower().split('=')[1]
                range_start, range_end = range_value.split('-')
                range_start = int(range_start) if range_start else 0
                range_end = int(range_end) if range_end else file_size - 1
                length = range_end - range_start + 1

                file_stream.seek(range_start)
                data = file_stream.read(length)
                file_stream.close()

                headers = [
                    ('Content-Type', 'video/mp4'),  # Adjust MIME type as needed
                    ('Content-Range', f'bytes {range_start}-{range_end}/{file_size}'),
                    ('Accept-Ranges', 'bytes'),
                    ('Content-Length', str(length)),
                    ('Content-Disposition', f'inline; filename="{file_name}"'),
                ]
                response = request.make_response(data, headers)
                response.status_code = 206
                return response
            else:
                # No Range header; send the whole file
                data = file_stream.read()
                file_stream.close()
                headers = [
                    ('Content-Type', 'video/mp4'),
                    ('Content-Length', str(file_size)),
                    ('Accept-Ranges', 'bytes'),
                    ('Content-Disposition', f'inline; filename="{file_name}"'),
                ]
                return request.make_response(data, headers)
        else:
            return request.make_response("File not found", status=404)
