import suds
import socket
import urllib2
import string
import os
import datetime
import base64

from tools.translate import _
from osv import osv

class AvaTaxService:

    def enable_log(self):
        import logging, tempfile
        logger = logging.getLogger('suds.client')
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.path.join(tempfile.gettempdir(), "soap-messages.log"))
        logger.propagate = False
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def __init__(self, username, password, url, timeout, enable_log=False):
        self.username = username    #This is the company's Development/Production Account number
        self.password = password #Put in the License Key received from AvaTax
        self.url = url
        self.timeout = timeout
        enable_log and self.enable_log()

    def create_tax_service(self):
        self.taxSvc = self.service('tax')
        return self

    def create_address_service(self):
        self.addressSvc = self.service('address')
        return self

    def service(self, name):
        nameCap = string.capitalize(name) # So this will be 'Tax' or 'Address'
        # The Python SUDS library can fetch the WSDL down from the server
        # or use a local file URL. We'll use a local file URL.
#        wsdl_url = 'file:///' + os.getcwd().replace('\\', '/') + '/%ssvc.wsdl.xml' % name
        # If you want to fetch the WSDL from the server, use this instead:
        wsdl_url = 'https://avatax.avalara.net/%s/%ssvc.wsdl' % (nameCap, nameCap)
        
        try:
             svc = suds.client.Client(url=wsdl_url)  
        except urllib2.URLError, details:
            raise osv.except_osv(_('Server Failed to Response'), _(details))
        else:
            svc.set_options(service='%sSvc' % nameCap)
            svc.set_options(port='%sSvcSoap' % nameCap)
            svc.set_options(location='%s/%s/%sSvc.asmx' % (self.url, nameCap, nameCap))
            svc.set_options(wsse=self.my_security(self.username, self.password))
            svc.set_options(soapheaders=self.my_profile())
            svc.set_options(timeout=self.timeout)
            return svc

    def my_security(self, username, password):
        token = suds.wsse.UsernameToken(username, password)

        # AvaTax leaves the WSSE Nonce and Created elements as
        # optional. As explained in XXX, you should include these if at
        # all possible, to make your connection more secure.
        # Nonce (optional) is a randomly generated, cryptographic token
        # used to prevent theft and replay attacks. We recommend sending
        # it if your SOAP client library supports it.
        token.setnonce()

        # Created (optional) identifies when the message was created and
        # prevents replay attacks. We recommend sending it if your SOAP
        # client library supports it.
        token.setcreated()
        security = suds.wsse.Security()
        security.tokens.append(token)
        return security

    def my_profile(self):

        # Set elements adapter defaults
        ADAPTER = 'Novapoint Group,0.1'

        # Profile Client.
        CLIENT = 'Novapoint Group,0.1'

        #Build the Profile element
        profileNameSpace = ('ns1', 'http://avatax.avalara.com/services')
        profile = suds.sax.element.Element('Profile', ns=profileNameSpace)
        profile.append(suds.sax.element.Element('Client', ns=profileNameSpace).setText(CLIENT))
        profile.append(suds.sax.element.Element('Adapter', ns=profileNameSpace).setText(ADAPTER))
        hostname = socket.gethostname()
        profile.append(suds.sax.element.Element('Machine', ns=profileNameSpace).setText(hostname))
        return profile

    def get_result(self, svc, operation, request):
        try:
            result = operation(request)
        except suds.WebFault, e:
            raise osv.except_osv(_('Error'), _(e.fault.faultstring))
        except urllib2.HTTPError, e:
            raise osv.except_osv(_('Server Failed to Response'), _(e.code))
        except urllib2.URLError, details:
            # We could also print the SOAP request here:
            # print svc.last_sent()
            raise osv.except_osv(_('Failed to reach the server'), _(details.reason))
        else:
            if (result.ResultCode != 'Success'):
                raise osv.except_osv(('Error'), _(AvaTaxError(result.ResultCode, result.Messages)))
            else:
                return result

    def ping(self):
        return self.get_result(self.taxSvc, self.taxSvc.service.Ping, '')

    def is_authorized(self):
        return self.get_result(self.taxSvc, self.taxSvc.service.IsAuthorized, 'GetTax,PostTax')

    def validate_address(self, baseaddress, textcase='Default'):
        # The Validate() operation needs a complex parameter, a
        # ValidateRequest. SUDS gives us a factory method on the service
        # object that creates a proxy class we can use.
        request = self.addressSvc.factory.create('ValidateRequest')
        # SUDS allows us to get defaults set up for us automatically. But
        # to keep this sample code simple, we won't do that here.
        # These are the elements required by the WSDL, with the defaults
        # set by the .NET adapter.
        # See the PHP sample code or .NET SDK Help File for what each of these is for.
        # TextCase, as with many other elements, is defined in the WSDL as
        # an enumeration. Depending on your SOAP client library, language
        # and platform, you may have these available to you. If you can
        # use enumerations rather than strings you should do so, because
        # it offers compile-time checking that can save your development
        # time. We're just using strings elsewhere in this sample code, to
        # keep things simple. But for TextCase we'll use SUDS
        # enumerations, just to show you how this sort of thing would
        # work.
        # This is the SUDS documentation on enumerations:
        # https://fedorahosted.org/suds/wiki/Documentation#ENUMERATIONS
        # So this is how we'll do things if we're just using strings
        #
        # request.TextCase = 'Default'
        #
        textCase = self.addressSvc.factory.create('TextCase')
        request.TextCase = textcase
        request.Coordinates = True
        request.Taxability = False
        request.Date = '2013-08-09'
        request.Address = baseaddress

        result = self.get_result(self.addressSvc, self.addressSvc.service.Validate, request)
        return result

    def get_tax(self, company_code, doc_date, doc_type, partner_code, doc_code, origin, destination,
               received_lines, exemption_no=None, customer_usage_type=None, salesman_code=None, commit=False, invoice_date=None, reference_code=None):
        lineslist = []
        request = self.taxSvc.factory.create('GetTaxRequest')
        # We'll first default everything just as the .NET adapter does
        request.Commit = commit
        request.DetailLevel = 'Diagnostic'
        request.Discount = 0.0
        request.ServiceMode = 'Automatic' # PHP defaults this to Automatic; Java likewise
        request.PaymentDate = '1900-01-01'
        request.ExchangeRate = 45
        request.ExchangeRateEffDate = '2011-07-07'
        request.HashCode = 0
        request.ReferenceCode = reference_code
        if invoice_date:
            taxoverride = self.taxSvc.factory.create('TaxOverride')
            taxoverride.TaxOverrideType = 'TaxDate'
            taxoverride.TaxDate = invoice_date
            taxoverride.TaxAmount = 0
            taxoverride.Reason = 'Return Items'
            request.TaxOverride = taxoverride
        # We'll now set the properties as we would normally, including
        # some that have already been defaulted.
        # The GetTax call will exactly match that in the PHP sample
        # code. So you can compare the XML from them line-by-line. We
        # suggest you try to get the same call set up in whatever language
        # and platform you're using, so you can compare your XML likewise.
        # See the PHP sample code for an explanation of each of these.
        request.CompanyCode = company_code
        request.DocDate = doc_date
        request.DocType = doc_type
        request.DocCode = doc_code
        request.CustomerCode = partner_code
        request.ExemptionNo = exemption_no
        request.CustomerUsageType = customer_usage_type
        request.SalespersonCode = salesman_code
        # Now the AddressCode, which we'll reference later. Note that
        # although it's a string and so you could use 'Origin' and
        # 'Destination' here, because addresses could be defined at the
        # line level you're best off just numbering them.
        #
        # Furthermore, any Messages you get back in an error from the
        # service will, in Message.RefersTo, reference the addresses
        # indexed as they appear in Addresses, starting at zero, so if you
        # use AddressCode = '0', '1' and so on, the index in the Message
        # will match the appropriate item.
        # Be very careful to make the addresscodes all match up. If, for
        # example, origin.AddressCode does not match an entry in
        # Addresses, the origin address will be treated as if it were
        # blank.
        # Now we'll set some of the other properties as usual
        addresses = self.taxSvc.factory.create('ArrayOfBaseAddress')
        addresses.BaseAddress = [origin, destination]
        request.Addresses = addresses
        request.OriginCode = '0' # Referencing an address above
        request.DestinationCode = '1' # Referencing an address above
        for line in range(0, len(received_lines)):
            line1 = self.taxSvc.factory.create('Line')
            line1.Qty = received_lines[line].get('qty', 1)
            line1.Discounted = False
            line1.No = '%d' %line
            line1.ItemCode = received_lines[line].get('itemcode', None)
            line1.Description = received_lines[line].get('description', None)
            line1.Amount = received_lines[line].get('amount', 0.0)
            line1.TaxCode = received_lines[line].get('tax_code', None)
            lineslist.append(line1)
        # So now we build request.Lines
        lines = self.taxSvc.factory.create('ArrayOfLine')
        lines.Line = lineslist
        request.Lines = lines
        # And we're ready to make the call
        result = self.get_result(self.taxSvc, self.taxSvc.service.GetTax, request)
        return result

    def cancel_tax(self, company_code, doc_code, doc_type, cancel_code):
        request = self.taxSvc.factory.create('CancelTaxRequest')
        request.CompanyCode = company_code
        request.DocCode = doc_code
        request.DocType = doc_type
        request.CancelCode = cancel_code
        result = self.get_result(self.taxSvc, self.taxSvc.service.CancelTax, request)
        return result

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class AvaTaxError(Error):
    """Exception raised for errors calling AvaTax.

    Attributes:
        resultCode -- result.ResultCode
        messages  -- result.Messages
    """

    def __init__(self, resultCode, messages):
        self.resultCode = resultCode
        self.messages = messages

    def __str__(self):
        str = ''
        for item in self.messages:
            message = item[1][0] # SUDS gives us the message in a list, in a tuple

            str = "Severity: %s\n\nDetails: %s\n\n RefersTo: %s\n\n Summary: %s" \
            % (message.Severity, message.Details, message.RefersTo, message.Summary)
        return str

class BaseAddress:

    def __init__(self, addSvc, Line1=None, Line2=None, City=None, PostalCode=None, Region=None, Country=None, AddressCode=None):
        self.data = addSvc.factory.create('BaseAddress')
        self.data.TaxRegionId = 0
        self.data.Line1 = Line1
        self.data.Line2 = Line2
        self.data.City = City
        self.data.PostalCode = PostalCode
        self.data.Region = Region
        self.data.Country = Country
        self.data.AddressCode = AddressCode

class Line:

    def __init__(self, taxSvc, ItemCode, Amount, Qty, Description=None, TaxCode=None):
        self.taxSvc = taxSvc
        # We're not setting No here
        self.data = self.defaultLine()
        self.data.ItemCode = ItemCode
        self.data.Amount = Amount
        self.data.Qty = Qty
        self.data.Description = Description
        self.data.TaxCode = TaxCode

    def defaultLine(self):
        line = self.taxSvc.factory.create('Line')
        line.Qty = 1
        line.Discounted = False
        return line

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: