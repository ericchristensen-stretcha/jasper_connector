# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

import odoo
from odoo.addons.jasper_connector.report.jasper import report_jasper

import logging
_logger = logging.getLogger(__name__)

KNOWN_PARAMETERS = [
    'OERP_ACTIVE_ID', 'OERP_ACTIVE_IDS',
    'OERP_COMPANY_NAME', 'OERP_COMPANY_LOGO', 'OERP_COMPANY_HEADER1',
    'OERP_COMPANY_FOOTER1', 'OERP_COMPANY_FOOTER2', 'OERP_COMPANY_WEBSITE',
    'OERP_COMPANY_CURRENCY', 'OERP_COMPANY_STREET', 'OERP_COMPANY_STREET2',
    'OERP_COMPANY_ZIP', 'OERP_COMPANY_CITY', 'OERP_COMPANY_COUNTRY',
    'OERP_COMPANY_PHONE', 'OERP_COMPANY_FAX', 'OERP_COMPANY_MAIL',
]


def registered_report(name):
    """ Register dynamicaly the report for each entry"""

    gname = 'report.' + name
    if gname in odoo.report.interface.report_int._reports:
        return
    report_jasper(gname)
    _logger.debug('Register the jasper report service [%s]' % name)

