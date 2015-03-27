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

from suds_client import AvaTaxService, BaseAddress, Line

class account_tax(osv.osv):
    """Inherit to implement the tax using avatax API"""
    _inherit = "account.tax"

    def _check_compute_tax(self, cr, uid, avatax_config, doc_date, doc_code, doc_type, partner, ship_from_address_id, shipping_address_id,
                          lines, shipping_charge, user=None, commit=False, invoice_date=False, reference_code=False, context=None):
#        address_obj = self.pool.get('res.partner.address')
        address_obj = self.pool.get('res.partner')
        
        #it's show destination address
        shipping_address = address_obj.browse(cr, uid, shipping_address_id, context=context)
        if not lines:
            raise osv.except_osv(_('Error !'), _('AvaTax needs atleast one sale order line defined for tax calculation.'))
        if avatax_config.force_address_validation:
            if not shipping_address.date_validation:
                raise osv.except_osv(_('Address Not Validated !'), _('Please validate the shipping address for the partner %s.'
                            % (partner.name)))
        if not ship_from_address_id:
            raise osv.except_osv(_('No Ship from Address Defined !'), _('There is no company address defined.'))
        if not shipping_address_id:
                raise osv.except_osv(_('No Shipping Address Defined !'), _('There is no shipping address defined for the partner.'))

        #it's show source address
        ship_from_address = address_obj.browse(cr, uid, ship_from_address_id, context=context)
        
#        shipping_address = address_obj.browse(cr, uid, shipping_address_id, context=context)
        if not ship_from_address.date_validation:
            raise osv.except_osv(_('Address Not Validated !'), _('Please validate the company address.'))

        #shipping charge calculation with product tax
        if shipping_charge:
            lines.append({
                'qty': 1,
                'amount': shipping_charge,
                'itemcode': '',
                'description': '',
                'tax_code': avatax_config.default_shipping_code_id.name
            })
        #For check credential
        avapoint = AvaTaxService(avatax_config.account_number, avatax_config.license_key,
                                 avatax_config.service_url, avatax_config.request_timeout, avatax_config.logging)
        avapoint.create_tax_service()
        addSvc = avapoint.create_address_service().addressSvc
        origin = BaseAddress(addSvc, ship_from_address.street or None,
                             ship_from_address.street2 or None,
                             ship_from_address.city, ship_from_address.zip,
                             ship_from_address.state_id and ship_from_address.state_id.code or None,
                             ship_from_address.country_id and ship_from_address.country_id.code or None, 0).data
        destination = BaseAddress(addSvc, shipping_address.street or None,
                                  shipping_address.street2 or None,
                                  shipping_address.city, shipping_address.zip,
                                  shipping_address.state_id and shipping_address.state_id.code or None,
                                  shipping_address.country_id and shipping_address.country_id.code or None, 1).data
        
        #using get_tax method to calculate tax based on address                          
        result = avapoint.get_tax(avatax_config.company_code, doc_date, doc_type,
                                 partner.name, doc_code, origin, destination,
                                 lines, partner.exemption_number or None,
                                 partner.exemption_code_id and partner.exemption_code_id.code or None,
                                 user and user.name or None, commit, invoice_date, reference_code)
        
        return result

    def cancel_tax(self, cr, uid, avatax_config, doc_code, doc_type, cancel_code):
         """Sometimes we have not need to tax calculation, then method is used to cancel taxation"""
         avapoint = AvaTaxService(avatax_config.account_number, avatax_config.license_key,
                                  avatax_config.service_url, avatax_config.request_timeout,
                                  avatax_config.logging)
         avapoint.create_tax_service()
         result = avapoint.cancel_tax(avatax_config.company_code, doc_code, doc_type, cancel_code)
         return result

account_tax()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
