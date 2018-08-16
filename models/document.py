# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

from StringIO import StringIO
from lxml import etree
import base64

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.tools.sql import drop_view_if_exists
from odoo.addons.jasper_connector.libs.common import \
    (registered_report, KNOWN_PARAMETERS)
from odoo.addons.jasper_connector.libs import jasperlib

import logging
_logger = logging.getLogger(__name__)

JRXML_NS = {
    'root': 'http://jasperreports.sourceforge.net/jasperreports',
}


class jasper_document_extension(models.Model):
    _name        = 'jasper.document.extension'
    _description = 'Jasper Document Extension'
    _order       = 'name'

    def dummy_function(self):
        return True

    # SOC #
    name        = fields.Char(string='Name', size=128, translate=True)
    jasper_code = fields.Char(string='Jasper Code', size=32, required=True)
    extension   = fields.Char(string='Extension', size=10, required=True)
    # EOC #


class jasper_document(models.Model):
    _name = 'jasper.document'
    _description = 'Jasper Document'
    _order = 'sequence'

    def _get_formats(self):
        """
        Return the list of all types of document that can be
        generate by JasperServer
        """
        extension_obj = self.env['jasper.document.extension']
        ext_ids = extension_obj.search([])
        ext = [(extension['jasper_code'],
                extension['name'] + " (*." + extension['extension'] + ")")
               for extension in ext_ids]
        return ext

    # SOC #
    name           =  fields.Char('Name', size=128, translate=True, required=True,
                                  placeholder="InvoiceJ")  # button name
    enabled        =  fields.Boolean('Enabled',
                                     help="Indicates if this document is active or not")
    model_id       =  fields.Many2one('ir.model', 'Object Model', required=True)
    server_id      =  fields.Many2one('jasper.server', 'Server',
                                      help='Select specific JasperServer')
    jasper_file    =  fields.Char('Jasper file',
                                   size=128,
                                   default='Unused option')  # jasper filename
    group_ids      =  fields.Many2many('res.groups', 'jasper_wizard_group_rel',
                                       'document_id', 'group_id', 'Groups', )
    depth          =  fields.Integer('Depth', required=True)
    format_choice  =  fields.Selection([('mono', 'Single Format'),
                                        ('multi', 'Multi Format')],
                                       'Format Choice',
                                       required=True,
                                       default='mono')
    format         =  fields.Selection(_get_formats, 'Formats',
                                       default='PDF')
    report_unit    =  fields.Char('Report Unit', size=128,
                                  help='Enter the name for report unit in Jasper Server')
    mode           =  fields.Selection([('sql', 'SQL'),
                                        ('xml', 'XML'),
                                        ('multi', 'Multiple Report')],
                                        'Mode',
                                        required=True,
                                        default='sql')
    before         =  fields.Text('Before',
                                 help='This field must be filled with a valid SQL request and will be executed BEFORE the report edition',)
    after          =  fields.Text('After',
                                  help='This field must be filled with a valid SQL request and will be executed AFTER the report edition',)
    attachment     =  fields.Char('Save As Attachment Prefix', size=255,
                                  help='This is the filename of the attachment used to store the printing result. \
                                        Keep empty to not save the printed reports. \
                                        You can use a python expression with the object and time variables.')
    attachment_use =  fields.Boolean('Reload from Attachment',
                                     help='If you check this, then the second time the user prints with same attachment name, \
                                           it returns the previous report.')
    param_ids      =  fields.One2many('jasper.document.parameter',
                                      'document_id', 'Parameters', )
    ctx            =  fields.Char('Context', size=128,
                                  help="Enter condition with context does match to see the print action\neg: context.get('foo') == 'bar'")
    sql_view       =  fields.Text('SQL View',
                                  help='Insert your SQL view, if the report is based on it')
    sql_name       =  fields.Char('Name of view', size=128, )
    child_ids      =  fields.Many2many('jasper.document',
                                       'jasper_document_multi_rel',
                                       'source_id',
                                       'destin_id',
                                       'Child report',
                                       help='Select reports to launch when this report is called')
    sequence       =  fields.Integer('Sequence',
                                     help='The sequence is used when launch a multple report, to select the order to launch',
                                     default=100)
    only_one       =  fields.Boolean('Launch one time for all ids',
                                     help='Launch the report only one time on multiple id')
    duplicate      =  fields.Char('Duplicate', size=256,
                                  help="Indicate the number of duplicate copie, use o as object to evaluate\neg: o.partner_id.copy\nor\n'1'",
                                  default='1')
    lang           =  fields.Char('Lang', size=256,
                                  help="Indicate the lang to use for this report, use o as object to evaluate\neg: o.partner_id.lang\n ctx as context\neg: ctx.get('test')\n or\n'fr_FR'\ndefault use user's lang")
    report_id      =  fields.Many2one('ir.actions.report.xml', 'Report link',
                                      readonly=True, help='Link to the report in ir.actions.report.xml')
    check_sel      =  fields.Selection([('none', 'None'),
                                        ('simple', 'Simple'),
                                        ('func', 'Function')],
                                      'Checking type',
                                      default='none',
                                      help='if None, no check\nif Simple, define on Check Simple the condition\n if function, the object have check_print function')
    check_simple   =  fields.Char('Check Simple', size=256,
                                  help="This code inside this field must return True to send report execution\neg o.state in ('draft', 'open')")
    message_simple =  fields.Char('Return message', size=256,
                                  translate=True,
                                  help="Error message when check simple doesn't valid")
    label_ids      =  fields.One2many('jasper.document.label', 'document_id',
                                      'Labels')
    pdf_begin      =  fields.Many2one(comodel_name='ir.attachment',
                                      string='PDF Banner at begin',
                                     )
    pdf_ended      =  fields.Many2one(comodel_name='ir.attachment',
                                      string='PDF Banner at end',
                                     )
    # EOC #

    def __init__(self, pool, cr):
        """
        Automaticaly registered service at server starts
        """
        super(jasper_document, self).__init__(pool, cr)

    def make_action(self):
        """
        Create an entry in ir_actions_report_xml
        and ir.values
        """
        act_report_obj = self.env['ir.actions.report.xml']

        doc = self
        if doc.report_id:
            _logger.info('Update "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.report_%d' % (doc.id,),
                'model': doc.model_id.model,
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': False,
            }
            doc.report_id.write(args)
        else:
            _logger.info('Create "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.report_%d' % (doc.id,),
                'model': doc.model_id.model,
                'report_type': 'jasper',
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': False,
            }
            report_id = act_report_obj.create(args)
            _logger.debug('Report creation: %s - %s', report_id.name, self.id)
            self.env.cr.execute("""UPDATE jasper_document SET report_id=%s
                                   WHERE id=%s""", (report_id.id, self.id))
            value = 'ir.actions.report.xml,' + str(report_id.id)
            # self.env['ir.model.data'].ir_set(
                # cr, uid, 'action', 'client_print_multi', doc.name,
                # [doc.model_id.model], value, replace=False, isobject=True)
            self.env['ir.values'].\
                create({
                        'name'  : doc.name,
                        'key'   : 'action',
                        'key2'  : 'client_print_multi',
                        'model' : doc.model_id.model,
                        'value' : value,
                        'model_id' : doc.model_id.id,
                       })
        registered_report('jasper.report_%d' % (doc.id,))

    def action_values(self):
        """
        Search ids for reports
        """
        args = [
            ('key', '=', 'action'),
            ('key2', '=', 'client_print_multi'),
            ('value', '=', 'ir.actions.report.xml,%d' % self.report_id.id),
        ]
        return self.env['ir.values'].search(args)

    def get_action_report(self, cr, uid, module, name, datas=None,
                          context=None):
        """
        Give the XML ID dans retrieve the report action

        :param module: name fo the module where the XMLID is reference
        :type module: str
        :param name: name of the XMLID (afte rthe dot)
        :type name: str
        :return: return an ir.actions.report.xml
        :rtype: dict
        """
        if context is None:
            context = {}

        if datas is None:
            datas = {}

        mod_obj = self.env['ir.model.data']
        result = mod_obj.get_object_reference(cr, uid, module, name)
        id = result and result[1] or False
        service = 'jasper.report_%d' % (id,)
        _logger.debug('get_action_report -> ' + service)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': service,
            'datas': datas,
            'context': context,
        }

    def create_values(self):
        if not self.action_values():
            self.make_action()
        return True

    def unlink_values(self):
        """
        Only remove link in ir.values, not the report
        """
        _logger.debug('unlink_values:%s', self)
        self.action_values().unlink()
        self.report_id.unlink()
        return True

    @api.model
    def create(self,vals):
        """
        Dynamicaly declare the wizard for this document
        """

        doc_id = super(jasper_document, self).create(vals)
        doc_id.make_action()

        # Check if view exists and create it in the database
        if vals.get('sql_name') and vals.get('sql_view'):
            drop_view_if_exists(cr, vals.get('sql_name'))
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (vals['sql_name'],
                                                              vals['sql_view'])
            self.env.cr.execute(sql_query)
        return doc_id

    def write(self, vals):
        """
        If the description change, we must update the action
        """

        if vals.get('sql_name') or vals.get('sql_view'):
            sql_name = vals.get('sql_name',
                                self[0].browse(cr, uid, ids[0]).sql_name)
            sql_view = vals.get('sql_view',
                                self.browse(cr, uid, ids[0]).sql_view)
            drop_view_if_exists(cr, sql_name)
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (sql_name,
                                                              sql_view)
            self.env.cr.execute(sql_query, (ids,))

        res = super(jasper_document, self).write(vals)

        if 'enabled' in vals:
            if vals['enabled']:
                for record in self:
                    _logger.debug('Request to create the report action: %s', record)
                    record.make_action()
            else:
                for record in self:
                    record.unlink_values()
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """
        When we duplicate code, we must remove some field, before
        """
        if context is None:
            context = {}

        if default is None:
            default = {}

        doc = self.browse(cr, uid, id, context=context)

        default['report_id'] = False
        default['name'] = doc.name + _(' (copy)')
        return super(jasper_document, self).copy(cr, uid, id, default,
                                                 context=context)

    def unlink(self):
        """
        When remove jasper_document, we must remove data to
        ir.actions.report.xml and ir.values
        """
        for doc in self:
            if doc.report_id:
                doc.unlink_values()
                doc.report_id.unlink()
        return super(jasper_document, self).unlink()

    def check_report(self):

        def compose_path(basename):
            return jss['prefix'] and '/' + jss['prefix'] + '/instances/%s/%s' or basename

        # TODO, use jasperlib to check if report exists
        curr = self
        js_server = self.env['jasper.server']
        if curr.server_id:
            jss = curr.server_id.browse()
        else:
            js_server_set = js_server.search([('enable', '=', True)])
            if not js_server_set:
                raise Warning(
                    _('No JasperServer configuration found !')
                )
            jss = js_server_set[0]

        try:
            js = jasperlib.Jasper(jss.host, jss.port, jss.user, jss['password'])
            js.auth()
            uri = compose_path('/openerp/bases/%s/%s') % (self.env.cr.dbname,
                                                          curr.report_unit)
            _logger.debug('Report URI: %s', uri)
            envelop = js.run_report(uri=uri, output='PDF', params={})
            js.send(jasperlib.SoapEnv('runReport', envelop).output())
        except jasperlib.ServerNotFound:
            raise Warning(
                _('Error, server not found %s %d') % (js.host, js.port))
        except jasperlib.AuthError:
            raise Warning(
                _('Error, Authentification failed for %s/%s') % (js.user,
                                                                 js.pwd))
        except jasperlib.ServerError, e:
            _logger.exception('Fatal exception')
            raise Warning(_('Fatal exception, please see log.'))

        return True

    def parse_jrxml(self, cr, uid, ids, content, context=None):
        """
        Parse JRXML file to retrieve I18N parameters and OERP parameters
        are not standard
        """
        label_obj = self.env['jasper.document.label']
        param_obj = self.env['jasper.document.parameter']
        att_obj = self.env['ir.attachment']

        fp = StringIO(content)
        tree = etree.parse(fp)
        param = tree.xpath('//root:parameter/@name', namespaces=JRXML_NS)
        for label in param:
            val = tree.xpath('//root:parameter[@name="' + label + '"]//root:defaultValueExpression', namespaces=JRXML_NS)[0].text
            _logger.debug('%s -> %s' % (label, val))

            if label.startswith('I18N_'):
                lab = label.replace('I18N_', '')
                label_ids = label_obj.search(cr, uid, [('name', '=', lab)],
                                             context=context)
                if label_ids:
                    continue
                label_obj.create(cr, uid, {
                    'document_id': ids[0],
                    'name': lab,
                    'value': val.replace('"', ''),
                }, context=context)
            if label.startswith('OERP_') and label not in KNOWN_PARAMETERS:
                lab = label.replace('OERP_', '')
                param_ids = param_obj.search(cr, uid, [('name', '=', lab)],
                                             context=context)
                if param_ids:
                    continue
                param_obj.create(cr, uid, {
                    'document_id': ids[0],
                    'name': lab,
                    'code': val.replace('"', ''),
                    'enabled': True,
                }, context=context)

        # Now we save JRXML as attachment
        # We retrieve the name of the report with the attribute name from the
        # jasperReport element
        filename = '%s.jrxml' % tree.xpath('//root:jasperReport/@name',
                                           namespaces=JRXML_NS)[0]

        att_ids = att_obj.search(
            cr, uid, [('name', '=', filename),
                      ('res_model', '=', 'jasper.document'),
                      ('res_id', '=', ids[0])], context=context)
        if att_ids:
            att_obj.unlink(cr, uid, att_ids, context=context)

        ctx = context.copy()
        ctx['type'] = 'binary'
        ctx['default_type'] = 'binary'
        att_obj.create(cr, uid, {'name': filename,
                                 'datas': base64.encodestring(content),
                                 'datas_fname': filename,
                                 'file_type': 'text/xml',
                                 'res_model': 'jasper.document',
                                 'res_id': ids[0]}, context=ctx)

        fp.close()
        return True


class jasper_document_parameter(models.Model):
    _name        = 'jasper.document.parameter'
    _description = 'Add parameter to send to jasper server'
    _order       = 'name'

    def dummy_function(self):
        return True

    # SOC #
    name        = fields.Char('Name', size=32, help='Name of the jasper parameter, the prefix must be OERP_', required=True)
    code        = fields.Char('Code', size=256, help='Enter the code to retrieve data', required=True)
    enabled     = fields.Boolean('Enabled', default=True)
    only_one    = fields.Boolean('One Run')
    multi       = fields.Boolean('Multi Run')
    selectable  = fields.Boolean('Selectable')
    document_id = fields.Many2one('jasper.document', 'Document',
                                  required=True)
    # EOC #


class jasper_document_label(models.Model):
    _name        = 'jasper.document.label'
    _description = 'Manage label in document, for different language'
    _order       = 'name'

    def dummy_function(self):
        return True

    # SOC #
    name        = fields.Char('Parameter', size=64, required=True,
                         help='Name of the parameter send to JasperServer, prefixed with I18N_\neg: test become I18N_TEST as parameter')
    value       =  fields.Char('Value', size=256, required=True, translate=True,
                         help='Name of the label, this field must be translated in all languages available in the database')
    document_id = fields.Many2one('jasper.document', 'Document',
                                  required=True)
    # EOC #
