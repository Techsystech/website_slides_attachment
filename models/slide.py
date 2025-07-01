# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64


class Slide(models.Model):
    _inherit = "slide.slide"

    video_source_type = fields.Selection(selection_add=([('local', 'Local File')]))

    is_local_video = fields.Boolean()

    video_binary_content = fields.Char(
        string='Video Attachment',
        help='Binary content of the video file to be streamed.'
    )

    @api.depends('video_source_type', 'is_local_video')
    def _compute_video_source_type(self):
        super()._compute_video_source_type()
        for slide in self:
            if slide.is_local_video:
                slide.video_source_type = 'local'
                
    #override
    def _compute_slide_icon_class(self):
        #first part coppied from original method, I know not good but super does not work here
        icon_per_slide_type = {
            'image': 'fa-file-picture-o',
            'article': 'fa-file-text-o',
            'quiz': 'fa-question-circle-o',
            'pdf': 'fa-file-pdf-o',
            'sheet': 'fa-file-excel-o',
            'doc': 'fa-file-word-o',
            'slides': 'fa-file-powerpoint-o',
            'youtube_video': 'fa-youtube-play',
            'google_drive_video': 'fa-play-circle-o',
            'vimeo_video': 'fa-vimeo',
        }
        for slide in self:
            slide.slide_icon_class = icon_per_slide_type.get(slide.slide_type, 'fa-file-o')

        for slide in self:
            if slide.slide_category == 'video' and slide.video_source_type == 'local':
                slide.slide_icon_class = icon_per_slide_type.get('youtube_video', 'fa-file-o')