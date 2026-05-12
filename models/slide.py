# -*- coding: utf-8 -*-

import base64
import logging
from pathlib import Path

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

LOCAL_ATTACHMENT_PREFIX = "ir.attachment:"


class Slide(models.Model):
    _inherit = "slide.slide"

    video_source_type = fields.Selection(selection_add=([('local', 'Local File')]))

    is_local_video = fields.Boolean()

    video_binary_content = fields.Char(
        string='Video Attachment',
        help='Local video attachment token. Legacy filesystem paths are migrated to ir.attachment tokens.'
    )

    @api.model
    def _local_video_attachment_token(self, attachment_id):
        return f"{LOCAL_ATTACHMENT_PREFIX}{int(attachment_id)}"

    @api.model
    def _local_video_attachment_id_from_token(self, token):
        token = (token or "").strip()
        if token.startswith(LOCAL_ATTACHMENT_PREFIX):
            token = token[len(LOCAL_ATTACHMENT_PREFIX):]
        elif not token.isdigit():
            return False
        try:
            return int(token)
        except ValueError:
            return False

    def _get_local_video_attachment(self):
        self.ensure_one()
        attachment_id = self._local_video_attachment_id_from_token(self.video_binary_content)
        if not attachment_id:
            return self.env['ir.attachment']
        attachment = self.env['ir.attachment'].sudo().browse(attachment_id).exists()
        if attachment and attachment.res_model == 'slide.slide' and attachment.res_id == self.id:
            return attachment
        return self.env['ir.attachment']

    def _get_legacy_local_video_path(self):
        self.ensure_one()
        value = (self.video_binary_content or "").strip()
        if not value or self._local_video_attachment_id_from_token(value):
            return False
        path = Path(value).expanduser().resolve()
        if path.is_file():
            return path
        return False

    @api.model
    def _migrate_legacy_local_video_files(self, base_path=False, delete_source=False, limit=False):
        """Move legacy filesystem-backed local videos into ir.attachment.

        base_path is optional and intentionally configurable for production. When
        provided, only files under that directory are migrated. Without it, the
        method migrates the absolute paths already stored on slide records, which
        matches the legacy addon behavior without hardcoding a server path.
        """
        base = Path(base_path).expanduser().resolve() if base_path else False
        domain = [
            ('is_local_video', '=', True),
            ('video_binary_content', '!=', False),
            ('video_binary_content', 'not ilike', LOCAL_ATTACHMENT_PREFIX + '%'),
        ]
        slides = self.search(domain, limit=limit or None)
        migrated = skipped = failed = 0
        for slide in slides:
            raw_value = (slide.video_binary_content or "").strip()
            try:
                path = Path(raw_value).expanduser().resolve()
                if base and base not in (path, *path.parents):
                    skipped += 1
                    _logger.warning("Skipping slide %s legacy video outside base path: %s", slide.id, path)
                    continue
                if not path.is_file():
                    skipped += 1
                    continue
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': path.name,
                    'type': 'binary',
                    'datas': base64.b64encode(path.read_bytes()),
                    'mimetype': 'video/mp4',
                    'res_model': 'slide.slide',
                    'res_id': slide.id,
                })
                slide.sudo().write({'video_binary_content': self._local_video_attachment_token(attachment.id)})
                if delete_source:
                    path.unlink(missing_ok=True)
                migrated += 1
            except Exception:
                failed += 1
                _logger.exception("Failed migrating legacy local video for slide %s from %s", slide.id, raw_value)
        return {'migrated': migrated, 'skipped': skipped, 'failed': failed}

    @api.depends('video_url', 'is_local_video')
    def _compute_video_source_type(self):
        super()._compute_video_source_type()
        for slide in self:
            if slide.is_local_video:
                slide.video_source_type = 'local'

    def _compute_slide_icon_class(self):
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
            if slide.slide_category == 'video' and slide.video_source_type == 'local':
                slide.slide_icon_class = icon_per_slide_type.get('youtube_video', 'fa-file-o')
