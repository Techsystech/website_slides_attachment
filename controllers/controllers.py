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

