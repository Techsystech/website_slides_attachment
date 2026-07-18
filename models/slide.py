# -*- coding: utf-8 -*-

import base64
import logging
import re
from pathlib import Path

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

LOCAL_ATTACHMENT_PREFIX = "ir.attachment:"


class Slide(models.Model):
    _inherit = "slide.slide"

    video_source_type = fields.Selection(
        selection_add=[('local', 'Local Video'), ('nextcloud', 'Nextcloud')],
        store=True, readonly=False,
        help="Select the source for this video. Choose 'Local Video' to upload a file from your device, or 'Nextcloud' to link a share URL.",
    )

    is_local_video = fields.Boolean(
        compute='_compute_is_local_video',
        store=True,
    )

    video_binary_content = fields.Char(
        string='Video Attachment',
        help='Local video attachment token. Legacy filesystem paths are migrated to ir.attachment tokens.'
    )

    nextcloud_download_url = fields.Char(
        string='Nextcloud Download URL',
        compute='_compute_nextcloud_download_url',
    )

    video_attachment_name = fields.Char(
        string='Attached File',
        compute='_compute_video_attachment_info',
    )

    video_attachment_mimetype = fields.Char(
        string='File Type',
        compute='_compute_video_attachment_info',
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
    def _migrate_legacy_local_video_files(self, base_path=None, delete_source=False, limit=False):
        """Move legacy filesystem-backed local videos into ir.attachment.

        base_path is optional and intentionally configurable for production. When
        provided, only files under that directory are migrated. When omitted, the
        method reads ``website_slides_attachment.migration_base_path`` from
        ``ir.config_parameter``. If neither is set, it falls back to the legacy
        behaviour of migrating all absolute paths stored on slide records.
        """
        if base_path is None:
            base_path = self.env['ir.config_parameter'].sudo().get_param(
                'website_slides_attachment.migration_base_path', ''
            )
        base = Path(base_path).expanduser().resolve() if base_path else False
        domain = [
            ('slide_category', '=', 'video'),
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
                    _logger.warning(
                        "Skipping slide %s legacy video outside base path: %s", slide.id, path
                    )
                    continue
                if not path.is_file():
                    skipped += 1
                    _logger.warning(
                        "Skipping slide %s legacy video (file not found): %s", slide.id, path
                    )
                    continue
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': path.name,
                    'type': 'binary',
                    'datas': base64.b64encode(path.read_bytes()),
                    'mimetype': 'video/mp4',
                    'res_model': 'slide.slide',
                    'res_id': slide.id,
                })
                slide.sudo().write({
                    'video_binary_content': self._local_video_attachment_token(attachment.id),
                    'video_source_type': 'local',
                })
                if delete_source:
                    path.unlink(missing_ok=True)
                migrated += 1
            except Exception:
                failed += 1
                _logger.exception(
                    "Failed migrating legacy local video for slide %s from %s", slide.id, raw_value
                )
        _logger.info(
            "Legacy local video migration finished: %s migrated, %s skipped, %s failed",
            migrated, skipped, failed,
        )
        return {'migrated': migrated, 'skipped': skipped, 'failed': failed}

    @api.depends('video_url')
    def _compute_video_source_type(self):
        # The base compute resets video_source_type whenever video_url changes
        # (every keystroke while typing, or on any form auto-save). We stash
        # the current value before super() so we can restore the user's explicit
        # selection when the URL is still being entered or empty.
        current_values = {slide.id: slide.video_source_type for slide in self}
        super()._compute_video_source_type()
        for slide in self:
            if slide.video_url and self._is_nextcloud_url(slide.video_url):
                slide.video_source_type = 'nextcloud'
            elif not slide.video_source_type and current_values.get(slide.id):
                # Base compute cleared our value because video_url is empty or
                # doesn't match a known pattern yet. Restore the user's choice
                # so auto-saves don't wipe the dropdown selection.
                slide.video_source_type = current_values[slide.id]

    @api.depends('video_source_type')
    def _compute_is_local_video(self):
        for slide in self:
            slide.is_local_video = slide.video_source_type == 'local'

    @api.model
    def _is_nextcloud_url(self, url):
        if not url:
            return False
        url = url.strip().lower()
        # Nextcloud share URLs come in two flavours:
        #   https://domain.com/index.php/s/<token>
        #   https://domain.com/s/<token>          (clean URLs / pretty URLs)
        return '/index.php/s/' in url or re.search(r'/s/[a-z0-9]+', url)

    @api.depends('video_url')
    def _compute_nextcloud_download_url(self):
        for slide in self:
            if slide.video_source_type == 'nextcloud' and slide.video_url:
                url = slide.video_url.strip().rstrip('/')
                slide.nextcloud_download_url = url + '/download'
            else:
                slide.nextcloud_download_url = False

    @api.depends('video_binary_content')
    def _compute_video_attachment_info(self):
        for slide in self:
            attachment = slide._get_local_video_attachment()
            if attachment:
                slide.video_attachment_name = attachment.name
                slide.video_attachment_mimetype = attachment.mimetype
            else:
                slide.video_attachment_name = False
                slide.video_attachment_mimetype = False

    @api.onchange('video_source_type')
    def _onchange_video_source_type(self):
        for slide in self:
            if slide.video_source_type == 'local':
                slide.video_url = False
            elif slide.video_source_type == 'nextcloud':
                slide.video_binary_content = False
            else:
                slide.video_binary_content = False

    def _compute_slide_icon_class(self):
        super()._compute_slide_icon_class()
        for slide in self:
            if slide.slide_category == 'video' and slide.video_source_type in ('local', 'nextcloud'):
                slide.slide_icon_class = 'fa-youtube-play'
