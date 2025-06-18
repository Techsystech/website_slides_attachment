# -*- coding: utf-8 -*-
# from odoo import http
# from odoo.http import request, content_disposition
# import os


# class WebsiteSlidesAttachment(http.Controller):
#     @http.route('/website_slides_attachment/website_slides_attachment', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_slides_attachment/website_slides_attachment/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_slides_attachment.listing', {
#             'root': '/website_slides_attachment/website_slides_attachment',
#             'objects': http.request.env['website_slides_attachment.website_slides_attachment'].search([]),
#         })

#     @http.route('/website_slides_attachment/website_slides_attachment/objects/<model("website_slides_attachment.website_slides_attachment"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_slides_attachment.object', {
#             'object': obj
#         })

import logging
from odoo import http
from odoo.http import request
from werkzeug.utils import wrap_file
import base64, os

_logger = logging.getLogger(__name__)

class UploadController(http.Controller):

    @http.route('/website_slides_attachment/upload', type='http', auth='user', csrf=False)
    def upload_file(self, **kwargs):
        file = request.httprequest.files.get('file')
        
        print('file is: ', file)
        content = file.read()
        filename = file.filename
        filename =  filename.replace(' ', '_')  # Replace spaces with underscores for the filename
        open(request.httprequest.form.get('save_location') + request.httprequest.form.get('res_model') + '_' + request.httprequest.form.get('res_id') + '_' + filename, 'ab').write(content)
        record = request.env['slide.slide'].search([('id', '=', int(request.httprequest.form.get('res_id')))])
        print(request.httprequest.form.get('res_id'))
        #_logger.info("Received file: %s", filename)


        # Return a success response
        return request.make_response("Upload successful", status=200)

    @http.route('/website_slides_attachment/remove', type='http', auth='user', csrf=False)
    def remove_file(self, **kwargs):
        file_path = request.httprequest.form.get('file_path')
        print('file_path is: ', file_path)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print('file removed')
            return request.make_response("File removed successfully", status=200)
        else:
            return request.make_response("File not found", status=404)

    @http.route('/website_slides_attachment/download/<int:id>/filename=<file_name>', type='http', auth='user', csrf=False)
    def download_file(self, id=None, file_name=None, **kwargs):
        #file_path = request.httprequest.form.get('file_path')
        slide = request.env['slide.slide'].search([('id', '=', id)])
        file_path = slide.video_binary_content
        print('file_path is: ', file_path)
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
