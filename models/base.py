# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

from odoo import models, fields, api
import odoo

from odoo.addons.jasper_connector.report.jasper import report_jasper
from odoo.addons.jasper_connector.libs.common import registered_report

import logging
_logger = logging.getLogger(__name__)


class ResLang(models.Model):
    _inherit = 'res.lang'

    js_pattern_date     = fields.Char(string='Pattern Date', size=32,
                                      help='Jasper pattern date')
    js_pattern_time     = fields.Char(string='Pattern Time', size=32,
                                      help='Jasper pattern time')
    js_pattern_datetime = fields.Char(string='Pattern Date Time', size=64,
                                      help='Jasper pattern datetime')
    js_pattern_currency = fields.Char(string='Pattern Currency', size=32,
                                      help='Jasper pattern currency')
    js_pattern_number   = fields.Char(string='Pattern Number', size=32,
                                      help='Jasper pattern number')


class ResGroups(models.Model):
    _inherit = 'res.groups'

    is_jasper = fields.Boolean(string='JasperServer',
                               help='Dedicate groups for JasperServer',
                               default=False)


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report.xml'

    # SOC #
    report_type = fields.Selection(selection_add=[('jasper', 'Jasper')])
    # EOC #

    def register_all(self, cursor):
        """
        Register all jasper report
        """
        _logger.info('====[REGISTER JASPER REPORT]========================')
        cursor.execute("""SELECT id, report_name
                            FROM ir_act_report_xml
                           WHERE report_type = 'jasper'""")
        records = cursor.dictfetchall()
        for record in records:
            registered_report(record['report_name'])
        _logger.info('====[END REGISTER JASPER REPORT]====================')
        return True

    @api.model_cr
    def _lookup_report(self, name):
        """
        Use new report function to detect old report and
        use custom python parser
        """
        if 'report.' + name in odoo.report.interface.report_int._reports:
            rp = odoo.report.interface.report_int._reports['report.' + name]  # noqa
            if not isinstance(rp, report_jasper):
                rp = None
        else:
            self.env.cr.execute("""SELECT * FROM ir_act_report_xml
                           WHERE report_name=%s AND report_type=%s""",
                       (name, 'jasper'))
            r = self.env.cr.dictfetchone()
            rp = r and report_jasper('report.'+r['report_name']) or None
        if rp:
            return rp
        return super(IrActionReport, self)._lookup_report(name)
