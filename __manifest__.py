# -*- coding: utf-8 -*-
{
    'name': "ELearning Local Video Streaming",

    'summary': "Enable video streaming in website slides from local attachments",

    'description': "Enable video streaming in website slides from local attachments",

    'author': "Techsystech",
    'website': "https://erp.techsystech.io",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0',

    # any module necessary for this one to work correctly
    'depends': ['base','website_slides'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/slide.xml',
    ],
    'assets': {
    'web.assets_frontend': [
        'website_slides_attachment/static/src/**',
    ],
},
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

