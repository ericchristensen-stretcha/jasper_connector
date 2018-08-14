# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

from odoo.report.interface import report_int
from openerp.osv.osv import except_osv
from odoo.addons.jasper_connector.report.report_soap import Report
from odoo.addons.jasper_connector.report.report_exception \
    import (JasperException)

import logging
_logger = logging.getLogger(__name__)


class report_jasper(report_int):
    """
    Extend report_int to use Jasper Server
    """

    def create(self, cr, uid, ids, datas, context=None):
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug('Call %s' % self.name)
        try:
            return Report(self,cr, uid, ids, datas, context=context).execute()
        except JasperException, e:
            raise except_osv(e.title, e.message)

report_jasper('report.print.jasper.server')
