# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.

from lxml.etree import Element, tostring
import os

from odoo import models, fields, _
from odoo.tools import ustr, config
from odoo.modules import get_module_path
import odoo
from odoo.addons.jasper_connector.libs import jasperlib


import logging
_logger = logging.getLogger(__name__)


def log_error(message):
    _logger.error(message)


class JasperServer(models.Model):
    """
    Class to store the Jasper Server configuration
    """
    _name = 'jasper.server'
    _description = 'Jasper server configuration'
    _rec_name = 'host'

    # SOC #
    host     = fields.Char('Host', size=128, required=True,
                           help='Enter hostname or IP address',
                           default='localhost')
    port     = fields.Integer('Port',
                              default='8080')
    user     = fields.Char('Username', size=128,
                           help='Enter the username for JasperServer user, by default is jasperadmin',
                           default='jasperadmin')
    password = fields.Char('Password', size=128,
                           help='Enter the password for the user, by defaul is jasperadmin',
                           default='jasperadmin')
    repo     = fields.Char('Repository', size=256, required=True,
                           help='Enter the address of the repository',
                           default='/jasperserver/services/repository')
    sequence = fields.Integer('Sequence',
                              default='10')
    enable   = fields.Boolean('Enable this Jasper Server connection',
                              help='Check this, if the server is available',)
    status   = fields.Char('Status', size=64,
                           help='Check the registered and authentification status')
    prefix   = fields.Char('Prefix', size=32,
                           help='If prefix is filled, the reportUnit must in the new tree, usefull on a share hosting',
                           default=False)
    # EOC #

    def __init__(self, pool, cr):
        """
        Check if analysis schema and temporal table is present in the database
        if not, create it
        """
        cr.execute("""show server_version""")
        pg_version = cr.fetchone()[0].split('.')
        pg_version = tuple([int(x) for x in pg_version])

        if pg_version >= (8, 3, 0):
            cr.execute("""SELECT count(*)
                          FROM   pg_namespace
                          WHERE  nspname='analysis'""")
            if not cr.fetchone()[0]:
                _logger.info('Analysis schema have been created !')
                cr.execute("""CREATE SCHEMA analysis;
                       COMMENT ON SCHEMA analysis
                       IS 'Schema use for customize view in Jasper BI';""")

            cr.execute("""SELECT count(*)
                          FROM   pg_tables
                          WHERE  schemaname = 'analysis'
                          AND    tablename='dimension_date'""")
            if not cr.fetchone()[0]:
                _logger.info('Analysis temporal table have been created !')
                cr.execute("""
    create table analysis.dimension_date as
    select to_number(to_char(x.datum, 'YYYYMMDD'), 'FM99999999') as id,
           to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD') as "date",
           extract(year from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "year",
           extract(month from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "month",
           extract(day from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day",
           extract(quarter from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "quarter",
           extract(week from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "week",
           extract(dow from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day_of_week",
           extract(isodow from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "iso_day_of_week",
           extract(doy from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day_of_year",
           extract(century from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "century"
    from
    (select to_date('2000-01-01','YYYY-MM-DD') + (to_char(m, 'FM9999999999')||' day')::interval as datum
     from   generate_series(0, 15000) m) x""")

        # Check if plpgsql language is installed, if not raise an error
        cr.execute("""select count(*) as "installed" from pg_language
                       where lanname='plpgsql';""")
        if not cr.fetchone()[0]:
            _logger.warn('Please installed plpgsql in your database, before update your OpenERP server!\nused for translation')

        # For some function, we must add plpythonu as language
        _logger.info("Admin role for the database: %s" % config.get('db_admin', 'oerpadmin'))
        cr.execute("""SELECT count(*) from pg_roles
                       WHERE rolname=%s and rolcanlogin=false;""",
                   (config.get('db_admin', 'oerpadmin'),))
        if not cr.fetchone()[0]:
            _logger.warn('Role admin not found, we cannot install plpython and function for jasperserver')
        else:
            # Check if plpythonu is installed
            cr.execute("""SET ROLE %s""", (config.get('db_admin', 'oerpadmin'),))
            cr.execute("""select count(*) as "installed" from pg_language
                           where lanname='plpythonu';""")
            if not cr.fetchone()[0]:
                # Install this language
                _logger.info('Add PL/Python for this database')
                cr.execute("""CREATE LANGUAGE plpythonu;""")
                cr.commit()

            fct_file = openerp.tools.misc.file_open(os.path.join(
                get_module_path('jasper_connector'), 'sql', 'plpython.sql'))
            try:
                query = fct_file.read() % {'db_user': config.get('db_user',
                                                                 'oerp')}
                cr.execute(query)
                cr.commit()
            finally:
                fct_file.close()
                cr.execute('RESET ROLE')

        super(JasperServer, self).__init__(pool, cr)

    def check_auth(self):
        """
        Check if we can join the JasperServer instance,
        send the authentification and check the result
        """
        _logger.debug('Function: check_auth %s', self)
        js_config = self.read()[0]
        _logger.debug('Serverconfig collected: %s', js_config)
        try:
            js = jasperlib.Jasper(host= js_config['host'],
                                  port= js_config['port'],
                                  user= js_config['user'],
                                  pwd = js_config['password'])
            js.auth()
        except jasperlib.ServerNotFound:
            message = _('Error, JasperServer not found at %s (port: %d)') % (js.host, js.port)
            _logger.error(message)
            return self.write({'status': message})
        except jasperlib.AuthError:
            message = _('Error, JasperServer authentification failed for user %s/%s') % (js.user, js.pwd)
            _logger.error(message)
            return self.write({'status': message})

        return self.write({'status': _('JasperServer Connection OK')})

    # ********************************************
    # This method creates an XML for Jasper Server
    # ********************************************
    # TODO: ban element per level
    ban = (
        'res.company', 'ir.model', 'ir.model.fields', 'res.groups',
        'ir.model.data', 'ir.model.grid', 'ir.model.access', 'ir.ui.menu',
        'ir.actions.act_window', 'ir.action.wizard', 'ir.attachment',
        'ir.cron', 'ir.rule', 'ir.rule.group', 'ir.actions.actions',
        'ir.actions.report.custom', 'ir.actions.report.xml', 'ir.actions.url',
        'ir.ui.view', 'ir.sequence', 'res.partner.event',
    )

    @staticmethod
    def format_element(element):
        """
        convert element in lowercase and replace space per _
        """
        return ustr(element).lower().replace(' ', '_')

    def generate_context(self, cr, uid, context=None):
        """
        generate xml with context header
        """
        f_list = (
            'context_tz', 'context_lang', 'name', 'signature', 'company_id',
        )

        # TODO: Use browse to add the address of the company
        user = self.env.get('res.users')
        usr = user.read(cr, uid, [uid], context=context)[0]
        ctx = Element('context')

        for val in usr:
            if val in f_list:
                e = Element(val)
                if usr[val]:
                    if isinstance(usr[val], list):
                        e.set('id', str(usr[val][0]))
                        e.text = str(usr[val][1])
                    else:
                        e.text = str(usr[val])
                ctx.append(e)

        return ctx

    def generate_xml(self, cr, uid, relation, id, depth, old_relation='',
                     old_field='', context=None):
        """
        Generate xml for an object recursively
        """
        if not context:
            context = {}
        irm = self.env.get('ir.model')
        if isinstance(relation, int):
            irm_ids = [relation]
        else:
            irm_ids = irm.search(cr, uid, [('model', '=', relation)])

        if not irm_ids:
            log_error('Model %s not found !' % relation)

        ##
        # We must ban some model
        #
        ban = (
            'res.company', 'ir.model', 'ir.model.fields', 'res.groups',
            'ir.model.data', 'ir.model.grid', 'ir.model.access', 'ir.ui.menu',
            'ir.actions.act_window', 'ir.action.wizard', 'ir.attachment',
            'ir.cron', 'ir.rule', 'ir.rule.group', 'ir.actions.actions',
            'ir.actions.report.custom', 'ir.actions.report.xml',
            'ir.actions.url', 'ir.ui.view', 'ir.sequence',
        )

        ##
        # If generate_xml was called by a relation field, we must keep
        # the original filename
        ir_model = irm.read(cr, uid, irm_ids[0])
        if isinstance(relation, int):
            relation = ir_model['model']

        irm_name = self.format_element(ir_model['name'])
        if old_field:
            x = Element(self.format_element(old_field), relation=relation,
                        id=str(id))
        else:
            x = Element(irm_name, id='%s' % id)

        if not id:
            return x

        if isinstance(id, (int, long)):
            id = [id]

        obj = self.env.get(relation)
        mod_ids = obj.read(cr, uid, id, context=context)
        mod_fields = obj.fields_get(cr, uid)
        for mod in mod_ids:
            for f in mod_fields:
                field = f.lower()
                name = mod_fields[f]['string']
                type = mod_fields[f]['type']
                value = mod[f]
                e = Element(field, label='%s' % self.format_element(name))
                if type in ('char', 'text', 'selection'):
                    e.text = value and unicode(value) or ''
                elif type == 'integer':
                    e .text = value and str(value) or '0'
                elif type == 'float':
                    e.text = value and str(value) or '0.0'
                elif type == 'date':
                    e.set('format', 'YYYY-mm-dd')
                    e.text = value or ''
                elif type == 'datetime':
                    e.set('format', 'YYYY-mm-dd HH:MM:SS')
                    e.text = value or ''
                elif type == 'boolean':
                    e.text = str(value)
                elif type == 'many2one':
                    if not isinstance(value, int):
                        value = value and value[0] or 0
                    # log_error('Current: %r Old: %r' %
                    # (mod_fields[f]['relation'], relation))
                    if depth > 0 and value and \
                       mod_fields[f]['relation'] != old_relation and \
                       mod_fields[f]['relation'] not in ban:
                        e = self.generate_xml(
                            cr, uid, mod_fields[f]['relation'], value,
                            depth - 1, relation, field)
                    else:
                        e.set('id', '%r' % value or 0)
                        if not isinstance(value, int):
                            e.text = str(mod[f][1])
                elif type in ('one2many', 'many2many'):
                    if depth > 0 and value and \
                       mod_fields[f]['relation'] not in ban:
                        for v in value:
                            x.append(self.generate_xml(
                                cr, uid, mod_fields[f]['relation'], v,
                                depth - 1, relation, field))
                        continue
                    else:
                        e.set('id', '%r' % value)
                elif type in ('binary', 'reference'):
                    e.text = 'Not supported'
                else:
                    log_error('OUPS un oubli %s: %s(%s)' % (field, name, type))
                x.append(e)
        return x

    def generator(self, cr, uid, model, id, depth, context=None):
        root = Element('data')
        root.append(self.generate_context(cr, uid, context=context))
        root.append(self.generate_xml(cr, uid, model, id, depth,
                                      context=context))
        return tostring(root, pretty_print=context.get('indent', False))
