# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(env, version):
    result = env['slide.slide'].sudo()._migrate_legacy_local_video_files()
    _logger.info("website_slides_attachment legacy local-video migration result: %s", result)
