# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(env, version):
    base_path = env['ir.config_parameter'].sudo().get_param(
        'website_slides_attachment.migration_base_path', ''
    )
    if base_path:
        _logger.info(
            "website_slides_attachment 18.0.1.4: migrating legacy videos with base_path=%s",
            base_path,
        )
    else:
        _logger.warning(
            "website_slides_attachment 18.0.1.4: migrating legacy videos without a base path. "
            "Set website_slides_attachment.migration_base_path to restrict file access."
        )
    result = env['slide.slide'].sudo()._migrate_legacy_local_video_files()
    _logger.info("website_slides_attachment 18.0.1.4 migration result: %s", result)
