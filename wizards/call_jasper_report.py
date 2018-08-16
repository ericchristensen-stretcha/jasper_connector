# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

import base64

from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class CallJasperReportParameter(models.TransientModel):
    _name = 'wiz.call.jasper.report.parameter'
    _description = 'JasperReport Parameters'

    # SOC #
    name     = fields.Many2one(comodel_name='jasper.document.parameter',
                            string='Report')
    value    = fields.Char('Parameter Value')
    upper_id = fields.Many2one(comodel_name='wiz.call.jasper.report',
                               string='Link')
    # EOC #


class CallJasperReport(models.TransientModel):
    _name = 'wiz.call.jasper.report'
    _description = 'Call a jasperReport'
    
    @api.onchange('name')
    def onchange_name(self):
        param_ids = self.name.param_ids.\
                    filtered(lambda r: r.enabled == True and \
                                       r.selectable == True and \
                                       (r.only_one == r.document_id.only_one or \
                                        r.multi != r.document_id.only_one)
                            )
        param_ids_array = []
        for param_id in param_ids:
            param_ids_array.append([0,0,{'name': param_id.id}])
        _logger.debug('Assembled parameters: %s', param_ids_array)
        self.param_ids = param_ids_array

    # SOC #
    name      = fields.Many2one(comodel_name='jasper.document',
                                string='Report')
    param_ids = fields.One2many(comodel_name='wiz.call.jasper.report.parameter',
                                inverse_name='upper_id',
                                string='Report Parameters')
    name_id       = fields.Integer(related='name.id', 
                                   string='ID of report')
    name_only_one = fields.Boolean(related='name.only_one', 
                                   string='Only One value')
    # EOC #

    def do_generate(self):
        self.ensure_one()
        for formdata in self:
            _logger.debug('Calling report: %s - %s', formdata.name.name, 'jasper.report_%d' % (formdata.name.id),)
            params = {}
            for param in formdata.param_ids:
                params[param.name.name.lower()] = param.value
            return {'type' : 'ir.actions.report.xml',
                    'report_name' : 'jasper.report_%d' % (formdata.name.id),
                    # 'datas' : {'ids' : mrp_ids,
                               # 'model' : 'mrp.production',
                               # },
                    'context' : { 'parameters' : params },
                    }
