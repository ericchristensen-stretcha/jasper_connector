# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

from odoo import models, fields, _
from odoo.exceptions import Warning


import logging
_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    def check_print(self):
        return (False,'It is not possible to generate the report')
