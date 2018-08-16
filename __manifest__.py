# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

{
    'name': 'JasperReports Server Connector',
    'summary' : 'Interfaces Odoo with JasperReports Server',
    'version': '1.0.0',
    'depends': ['base',],
    'author': 'Noviat nv',
    'category': 'Others',
    'website': 'http://www.noviat.com',

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/base.xml',
        'views/base_view.xml',
        'data/jasper_document_extension.xml',
        # 'wizards/wizard.xml',
        'wizards/call_jasper_report_view.xml',
        'wizards/load_file_view.xml',
        'views/server.xml',
        'views/document.xml',
    ],
    # pip install python-dime
    'external_dependencies': {'python': ['dime', 'httplib2', 'pyPdf']},
    'demo': [],
    'images': [],
    'installable': True,
    'auto_install': False,
}
