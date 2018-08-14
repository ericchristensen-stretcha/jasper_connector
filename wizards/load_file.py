# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

import base64

from odoo import models, fields


class LoadFile(models.TransientModel):
    _name = 'load.jrxml.file'
    _description = 'Load file in the jasperdocument'

    # SOC #
    datafile = fields.Binary(string='File', 
                             required=True,
                             help='Select file to transfer')
    # EOC #

    def import_file(self):
        this = self
        content = base64.decodestring(this.datafile)
        self.env['jasper.document'].parse_jrxml(
            cr, uid, context.get('active_ids'), content, context=context)
        return True
