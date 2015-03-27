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
from osv import osv, fields
from tools.translate import _
import decimal_precision as dp

class sale_order(osv.osv):
    _inherit = "sale.order"

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        currency_obj = self.pool.get('res.currency')
        res = {}
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        res = super(sale_order, self)._amount_all(cr, uid, ids, field_name, arg, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            if avatax_config and not avatax_config.disable_tax_calculation and \
                avatax_config.default_tax_schedule_id.id == order.partner_id.tax_schedule_id.id:

                res[order.id] = {
                    'amount_untaxed': 0.0,
                    'amount_tax': 0.0,
                    'amount_total': 0.0,
                }
                for line in order.order_line:
                  res[order.id]['amount_untaxed'] += line.price_subtotal
                res[order.id]['amount_tax'] = currency_obj.round(cr, uid, order.pricelist_id.currency_id, order.tax_amount)
                res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Untaxed Amount',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax."),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Taxes',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Total',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
          'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Sale Price')),
    }

    def create_lines(self, cr, uid, order_lines):
        lines = []
        for line in order_lines:
            lines.append({
                'qty': line.product_uom_qty,
                'itemcode': line.product_id and line.product_id.default_code or None,
                'description': line.name,
                'amount': line.price_unit * (1-(line.discount or 0.0)/100.0) * line.product_uom_qty,
                'tax_code': line.product_id and ((line.product_id.tax_code_id and line.product_id.tax_code_id.name) or
                        (line.product_id.categ_id.tax_code_id  and line.product_id.categ_id.tax_code_id.name)) or None
            })
        return lines

    def compute_tax(self, cr, uid, ids, context=None):
        avatax_config_obj = self.pool.get('account.salestax.avatax')
        account_tax_obj = self.pool.get('account.tax')
        avatax_config = avatax_config_obj._get_avatax_config_company(cr, uid)
        partner_obj = self.pool.get('res.partner')

        for order in self.browse(cr, uid, ids):
            if avatax_config and not avatax_config.disable_tax_calculation and \
            avatax_config.default_tax_schedule_id.id == order.partner_id.tax_schedule_id.id:
            
#                address = partner_obj.address_get(cr, uid, [order.company_id.partner_id.id], ['contact'])
                lines = self.create_lines(cr, uid, order.order_line)
                tax_amount = account_tax_obj._check_compute_tax(cr, uid, avatax_config, order.date_confirm or order.date_order,
                                                                order.name, 'SalesOrder', order.partner_id, order.company_id.partner_id.id,
                                                                order.partner_id.id, lines, order.shipcharge, order.user_id,
                                                                context=context).TotalTax
                self.write(cr, uid, [order.id], {'tax_amount': tax_amount, 'order_line': []})
        return True

    def button_dummy(self, cr, uid, ids, context=None):
        self.compute_tax(cr, uid, ids, context=context)
        return super(sale_order, self).button_dummy(cr, uid, ids, context=context)

    def action_wait(self, cr, uid, ids, *args):
        res = super(sale_order, self).action_wait(cr, uid, ids)
        self.compute_tax(cr, uid, ids)
        return True

sale_order()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
