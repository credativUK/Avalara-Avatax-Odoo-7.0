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

{
    "name" : "Use AvaTax web service to calculate tax",
    "version" : "1.0",
    "author" : 'Pragmatic Team',
    "description": """ This module supports calculating sales and use taxes, validates addresses
using the AvaTax subscription service from AVALARA. www.avalara.com. It is targeted for the US, Canadian, and in the future the international markets
supported by AVALARA. Users of the module need to subscribe to a service plan from AVALARA and obtain the proper login credentials prior
to using this module. As the US and Canadian tax programs have more
than 22,000 unique tax jurisdictions based on a GEO-Location matrix segmented by product category,
and tax collection legislation continues to change in the US to include new
areas like internet transactions, we believe using a tax service from AvaTax to calculate applicable taxes due simplifies
a company's management, time and effort to be in compliance with tax rules.

It is intended that the tax calculation service is called whenever an existing tax calculation is calculated within OpenERP.

The process to setup the system is as follows:
A company would initially install the module.
A company would sign-up for the AVATAX service.
A company enter their AVATAX credentials in OpenERP.
A company then should setup their Chart of Accounts with the appropriate accounts to capture detailed tax information (see your accountant).
A company then sets up the AVATAX service to cater to the products and services they provide.
A company then configures OpenERP properly for tax processing with AVATAX.
A company then tests the AVATAX connection and service.

AVATAX also offers a service to manage the submission of taxes due to various tax jurisdictions electronically, and manually.

Please review the module documentation prior to installing the module for prerequisites.

NOTE: Use of this module is "at your own risk", and does not in any way make NovaPoint Group or OpenERP liable for any issues or construe any
obligation that calculations are correct, or that tax calculations are sufficient to meet regulatory or legislative requirements.

""",
    "category" : "Generic Modules/Accounting",
    "website" : "http://www.pragtech.co.in/",
    "depends" : ["sale_negotiated_shipping", 'account', 'account_accountant'],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
    "account_salestax_avatax_data.xml",
    "wizard/account_salestax_avatax_ping.xml",
    "wizard/account_salestax_avatax_address_validate.xml",
    "account_salestax_avatax_view.xml",
    "partner_view.xml",
    "product_view.xml",
    "account_invoice_workflow.xml",
    "account_invoice_view.xml",
    "security/account_salestax_avatax_security.xml",
    "security/ir.model.access.csv",
    ],
    "test" : [],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
