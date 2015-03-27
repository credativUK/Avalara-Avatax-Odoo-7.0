# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 NovaPoint Group LLC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import string

from osv import osv, fields
from tools.translate import _
import decimal_precision as dp

class account_invoice(osv.osv):
    """Inherit to implement the tax calculation using avatax API"""
    _inherit = "account.invoice"

    def _avatax_calc(self, cr, uid, ids, name, args, context=None):
        res = {}
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)

        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.type in ['out_invoice', 'out_refund'] and \
            avatax_config and not avatax_config.disable_tax_calculation and \
            avatax_config.default_tax_schedule_id.id == invoice.partner_id.tax_schedule_id.id:
                res[invoice.id] = True
            else:
                res[invoice.id] = False
        return res

    _columns = {
        'invoice_doc_no': fields.char('Invoice No', size=32, readonly=True, states={'draft':[('readonly',False)]}, help="Reference of the invoice"),
        'invoice_date': fields.date('Invoice Date', readonly=True),
        'avatax_calc': fields.function(_avatax_calc, method=True, string='Avatax Calculation', type='boolean', store=True)
    }
    
    def action_commit_tax(self, cr, uid, ids, context=None):
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        account_tax_obj = self.pool.get('account.tax')
        partner_obj = self.pool.get('res.partner')
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.avatax_calc:
                avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
                sign = invoice.type == 'out_invoice' and 1 or -1
                lines = self.create_lines(cr, uid, invoice.invoice_line, sign)
#                address = partner_obj.address_get(cr, uid, [invoice.company_id.partner_id.id], ['contact'])
                account_tax_obj._check_compute_tax(cr, uid, avatax_config, invoice.date_invoice,
                                                   invoice.internal_number, not invoice.invoice_doc_no and 'SalesInvoice' or 'ReturnInvoice',
                                                   invoice.partner_id, invoice.company_id.partner_id.id,
                                                   invoice.partner_id.id, lines, invoice.shipcharge, invoice.user_id,
                                                   True, invoice.invoice_date,
                                                   invoice.invoice_doc_no, context=context)
        return True

    def create_lines(self, cr, uid, invoice_lines, sign):
        lines = []
        for line in invoice_lines:
            lines.append({
                'qty': line.quantity,
                'itemcode': line.product_id and line.product_id.default_code or None,
                'description': line.name,
                'amount': sign * line.price_unit * (1-(line.discount or 0.0)/100.0) * line.quantity,
                'tax_code': line.product_id and ((line.product_id.tax_code_id and line.product_id.tax_code_id.name) or
                        (line.product_id.categ_id.tax_code_id  and line.product_id.categ_id.tax_code_id.name)) or None
            })
        return lines

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):
        refund_ids = super(account_invoice, self).refund(cr, uid, ids, date, period_id, description, journal_id)
        invoice = self.browse(cr, uid, ids[0])
        if invoice.avatax_calc:
            self.write(cr, uid, refund_ids[0], {
                'invoice_doc_no': invoice.internal_number,
                'invoice_date': invoice.date_invoice
                })
        return refund_ids

    def action_cancel(self, cr, uid, ids, *args):
        account_tax_obj = self.pool.get('account.tax')
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        res = super(account_invoice, self).action_cancel(cr, uid, ids, *args)

        for invoice in self.browse(cr, uid, ids, *args):
            if invoice.avatax_calc and invoice.internal_number:
                avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
                doc_type = invoice.type == 'out_invoice' and 'SalesInvoice' or 'ReturnInvoice'
                account_tax_obj.cancel_tax(cr, uid, avatax_config, invoice.internal_number, doc_type, 'DocVoided')
        return res

#    def check_tax_lines(self, cr, uid, inv, compute_taxes, ait_obj):
#        super(account_invoice, self).check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)
#        if inv.avatax_calc:
#            for tax in inv.tax_line:
#                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
#                if abs(compute_taxes[key]['amount'] - tax.amount) > inv.company_id.currency_id.rounding:
#                    raise osv.except_osv(_('Warning !'), _('Tax amount different !\nClick on compute to update tax base'))
    def check_tax_lines(self, cr, uid, inv, compute_taxes, ait_obj):
        if not inv.tax_line:
            for tax in compute_taxes.values():
                ait_obj.create(cr, uid, tax)
        else:
            tax_key = []
            for tax in inv.tax_line:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                tax_key.append(key)
                if not key in compute_taxes:
                    raise osv.except_osv(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if abs(base - tax.base) > inv.company_id.currency_id.rounding:
                    raise osv.except_osv(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if not key in tax_key:
                    raise osv.except_osv(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))
        
#        super(account_invoice, self).check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)
        if inv.avatax_calc:
            for tax in inv.tax_line:
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                if abs(compute_taxes[key]['amount'] - tax.amount) > inv.company_id.currency_id.rounding:
                    raise osv.except_osv(_('Warning !'), _('Tax amount different !\nClick on compute to update tax base'))

account_invoice()

class account_invoice_tax(osv.osv):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice_id, context=None):
        """compute tax after validate partner address, company credential and tax id and state"""
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        invoice_obj = self.pool.get('account.invoice')
        partner_obj = self.pool.get('res.partner')
        account_tax_obj = self.pool.get('account.tax')
        jurisdiction_code_obj = self.pool.get('jurisdiction.code')
        cur_obj = self.pool.get('res.currency')
        state_obj = self.pool.get('res.country.state')
        
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        tax_grouped = {}
        if invoice.avatax_calc:
            vals = {}
            cur = invoice.currency_id
            company_currency = invoice.company_id.currency_id.id
            lines = invoice_obj.create_lines(cr, uid, invoice.invoice_line, 1)
            avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
            
            # to check for company address
            company_address = partner_obj.address_get(cr, uid, [invoice.company_id.partner_id.id], ['default'])
            for tax in account_tax_obj._check_compute_tax(cr, uid, avatax_config,
                                                          invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                                          invoice.internal_number, 'SalesOrder', invoice.partner_id,
                                                          invoice.company_id.partner_id.id, invoice.partner_id.id,
                                                          lines, invoice.shipcharge, invoice.user_id, False,
                                                          invoice.date_invoice or time.strftime('%Y-%m-%d'),
                                                          context=context).TaxSummary[0]:
                val = {}
                state_ids = state_obj.search(cr, uid, [('code', '=', tax.Region)], context=context)
                state_id = state_ids and state_ids[0] or False
                jurisdiction_code_ids = jurisdiction_code_obj.search(cr, uid, [('type', '=', tax['JurisType'].lower()),
                                                                    ('tax_schedule_id', '=', avatax_config.default_tax_schedule_id.id),
                                                                    ('state_id', '=', state_id)],
                                                                    context=context)
                if not jurisdiction_code_ids:
                    raise osv.except_osv(
                    _('Jurisdiction Code is not defined !'),
                    _('You must define a jurisdiction code for %s type for %s state in the tax schedule for %s.'
                      % (tax['JurisType'], tax['Region'], avatax_config.default_tax_schedule_id.name)))
                jurisdiction_code = jurisdiction_code_obj.browse(cr, uid, jurisdiction_code_ids[0], context=context)

                val['invoice_id'] = invoice.id
                val['name'] = tax['TaxName'] or '/'
                val['amount'] = tax['Tax']
                val['manual'] = False
                val['base'] = tax['Base']
                if invoice.type == 'out_invoice':
                    val['base_code_id'] = jurisdiction_code.base_code_id.id
                    val['tax_code_id'] = jurisdiction_code.tax_code_id.id
                    val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id,
                                                         company_currency, val['base'] * jurisdiction_code.base_sign,
                                                         context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id,
                                                        company_currency, val['amount'] * jurisdiction_code.tax_sign,
                                                        context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = jurisdiction_code.account_collected_id.id
                    val['base_sign'] = jurisdiction_code.base_sign
                else:
                    val['base_code_id'] = jurisdiction_code.ref_base_code_id.id
                    val['ref_base_code_id'] = jurisdiction_code.ref_base_code_id.id
                    val['tax_code_id'] = jurisdiction_code.ref_tax_code_id.id
                    val['base_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id,
                                                         company_currency, val['base'] * jurisdiction_code.ref_base_sign,
                                                         context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id,
                                                        company_currency, val['amount'] * jurisdiction_code.ref_tax_sign,
                                                        context={'date': invoice.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = jurisdiction_code.account_paid_id.id
                    val['ref_base_sign'] = jurisdiction_code.ref_base_sign

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']
            for t in tax_grouped.values():
                t['base'] = cur_obj.round(cr, uid, cur, t['base'])
                t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
                t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
                t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
            return tax_grouped
        return super(account_invoice_tax, self).compute(cr, uid, invoice_id, context=context)

account_invoice_tax()

class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        invoice_obj = self.pool.get('account.invoice')
        ait_obj = self.pool.get('account.invoice.tax')
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        company_currency = invoice.company_id.currency_id.id

        if invoice.avatax_calc:
            for line in invoice.invoice_line:
                mres = self.move_line_get_item(cr, uid, line, context)
                if not mres:
                    continue
                res.append(mres)
                tax_code_found= False

                for tax in ait_obj.compute(cr, uid, invoice_id, context=context).values():
                    if invoice.type == 'out_invoice':
                        tax_code_id = tax['base_code_id']
                        tax_amount = line.price_subtotal * tax['base_sign']
                    else:
                        tax_code_id = tax['ref_base_code_id']
                        tax_amount = line.price_subtotal * tax['ref_base_sign']

                    if tax_code_found:
                        if not tax_code_id:
                            continue
                        res.append(self.move_line_get_item(cr, uid, line, context))
                        res[-1]['price'] = 0.0
                        res[-1]['account_analytic_id'] = False
                    elif not tax_code_id:
                        continue
                    tax_code_found = True

                    res[-1]['tax_code_id'] = tax_code_id
                    res[-1]['tax_amount'] = cur_obj.compute(cr, uid, invoice.currency_id.id, company_currency,
                                                            tax_amount, context={'date': invoice.date_invoice})

        else:
            res = super(account_invoice_line, self).move_line_get( cr, uid, invoice_id, context=context)
        return res

account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: