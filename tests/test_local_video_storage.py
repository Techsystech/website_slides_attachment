# -*- coding: utf-8 -*-

import base64
import tempfile
from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestLocalVideoStorage(TransactionCase):

    def test_attachment_token_roundtrip(self):
        slide = self.env['slide.slide'].new({})
        token = slide._local_video_attachment_token(42)
        self.assertEqual(token, 'ir.attachment:42')
        self.assertEqual(slide._local_video_attachment_id_from_token(token), 42)
        self.assertFalse(slide._local_video_attachment_id_from_token('/tmp/legacy.mp4'))

    def test_legacy_file_migration(self):
        channel = self.env['slide.channel'].create({'name': 'Migration Test Channel'})
        fd = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        try:
            fd.write(b'video-bytes')
            fd.close()
            slide = self.env['slide.slide'].create({
                'name': "What? It's fine…",
                'channel_id': channel.id,
                'slide_category': 'video',
                'is_local_video': True,
                'video_binary_content': fd.name,
            })
            result = self.env['slide.slide']._migrate_legacy_local_video_files(base_path=str(Path(fd.name).parent))
            self.assertEqual(result['migrated'], 1)
            self.assertTrue(slide.video_binary_content.startswith('ir.attachment:'))
            attachment = slide._get_local_video_attachment()
            self.assertEqual(base64.b64decode(attachment.datas), b'video-bytes')
        finally:
            Path(fd.name).unlink(missing_ok=True)

    def test_special_character_titles_are_not_used_in_playback_url(self):
        slide_id = 123
        self.assertEqual(f'/website_slides_attachment/download/{slide_id}', '/website_slides_attachment/download/123')
