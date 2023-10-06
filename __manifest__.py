# -*- coding: utf-8 -*-

{
    'name' : 'Beta Hooks',
    'version' : '1.0.0',
    'category': 'Sales/CRM',
    'summary': 'For sending updates to customer from odoo to beta',
    'description': """For sending updates to customer from odoo to beta""",
    'author': "Vinay",
    'website': "https://www.youngman.co.in/",
    'sequence': -100,
    "external_dependencies": {"python": ["mysql.connector"], "bin": []},
    'depends': ['base', 'jobsites', 'youngman_customers', 'ym_sms','sh_sale_dynamic_approval'],

    'data': [
        'views/views.xml',
        'security/ir.model.access.csv',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}
