# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

import logging
import mysql.connector
from mysql.connector import Error

import datetime, mimetypes

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError, ValidationError

from odoo.exceptions import UserError


def get_create_by(created_by_result):
    if not created_by_result or len(created_by_result) == 0:
        raise UserError("Your account does not exist in beta")
    else:
        return created_by_result[0]


def get_beta_customer_id(customer_id_result):
    if not customer_id_result or len(customer_id_result) == 0:
        raise UserError("This branch has not been created in beta")
    else:
        return customer_id_result[0]

def get_beta_godown_id(godown_result):
    if not godown_result or len(godown_result) == 0:
        raise UserError("Either of billing or parent godown is not present in beta")
    else:
        return godown_result[0]

def get_quotation_insert_query():
    return "INSERT INTO quotations (created_by, customer_id, contact_name, phone_number, site_name, price_type, total, freight, gstn, billing_address_line, billing_address_city, billing_address_pincode, delivery_address_line, delivery_address_city, delivery_address_pincode, delivery_date, pickup_date, security_amt, freight_payment, godown_id, crm_account_id, created_at, updated_at) VALUES (%(created_by)s, %(customer_id)s, %(contact_name)s, %(phone_number)s, %(site_name)s, %(price_type)s, %(total)s, %(freight)s, %(gstn)s, %(billing_address_line)s, %(billing_address_city)s, %(billing_address_pincode)s, %(delivery_address_line)s, %(delivery_address_city)s, %(delivery_address_pincode)s, %(delivery_date)s, %(pickup_date)s, %(security_amt)s, %(freight_payment)s, %(godown_id)s, %(crm_account_id)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"


def get_quotation_items_insert_query():
    return "insert into quotation_items (quotation_id, item_code, unit_price, quantity, created_at, updated_at) VALUES (%(quotation_id)s, %(item_code)s, %(unit_price)s, %(quantity)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"


def get_beta_user_id_from_email_query():
    return "select id from users where LOWER(email) = %s"


def get_beta_customer_id_from_gstn():
    return "select id from customers where UPPER(gstn) = %s"


def get_location_insert_query():
    return "INSERT INTO locations (location_name, type, state_code) VALUES (%s, 'job_order', %s)"

def get_state_code_from_state_alpha_query(state_code):
    return "SELECT state_code FROM states WHERE state_alpha = '{}'".format(state_code)

def get_order_insert_query():
    return "INSERT INTO orders (quotation_id, customer_id, job_order, po_no, place_of_supply, gstn, security_cheque, rental_advance, rental_order, godown_id, freight_amount, billing_godown, created_by, total, created_at, updated_at) VALUES (%(quotation_id)s, %(customer_id)s, %(job_order)s, %(po_no)s, %(place_of_supply)s, %(gstn)s, %(security_cheque)s, %(rental_advance)s, %(rental_order)s, %(godown_id)s, %(freight_amount)s, %(billing_godown)s, %(created_by)s, %(total)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"

def get_beta_godown_id_by_name_query(godown_name):
    return "SELECT id from locations where type='godown' and location_name = '{}'".format(godown_name)

def get_update_quotation_with_order_query():
    return "UPDATE quotations set order_id = %s where id = %s"


def get_order_po_insert_query():
    return "INSERT INTO order_po(order_id, po_no, po_amt, balance) VALUES (%s, %s, %s, %s)"


def get_order_po_details_insert_query():
    return "INSERT INTO order_po_details(order_id, po_no, po_date , item_code , quantity) VALUES (%(order_id)s,%(po_no)s,%(po_date)s,%(item_code)s,%(quantity)s)"


def get_billing_process_insert_query():
    return "insert into billing_process (order_id, site_contact, odoo_site_contact, office_contact, odoo_office_contact, bill_submission_location, site_address, site_pincode, office_address, office_pincode, process, po_required, challan_required) " \
           "VALUES (%(order_id)s, NULL, %(odoo_site_contact)s,NULL,%(odoo_office_contact)s,%(bill_submission_location)s,%(site_address)s,%(site_pincode)s,%(office_address)s,%(office_pincode)s,%(process)s, NULL, NULL)"


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        self._validate_order_before_confirming()

        try:
            connection = self._get_connection()
            connection.autocommit = False
            cursor = connection.cursor()
            email = "1rajeshretail@gmail.com" #self.env.user.email.lower()

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Get created by from beta")
            cursor.execute(get_beta_user_id_from_email_query(), [email])
            created_by = get_create_by(cursor.fetchone())

            if self.partner_id.team_id.name == 'INSIDE SALES':
                created_by = 568

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Get customer id from beta")
            cursor.execute(get_beta_customer_id_from_gstn(), [self.customer_branch.gstn])
            customer_id = get_beta_customer_id(cursor.fetchone())

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Get billing godown id from beta")
            cursor.execute(get_beta_godown_id_by_name_query(self.bill_godown.name))
            beta_bill_godown_id = get_beta_godown_id(cursor.fetchone())

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Get parent godown id from beta")
            cursor.execute(get_beta_godown_id_by_name_query(self.godown.name))
            beta_godown_id = get_beta_godown_id(cursor.fetchone())

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Trying to save quotation")
            quotation = self.get_quotation_data(created_by, customer_id, beta_godown_id)
            cursor.execute(get_quotation_insert_query(), quotation)
            quotation_id = cursor.lastrowid
            _logger.info("evt=SEND_ORDER_TO_BETA msg=Quotation saved with id" + str(quotation_id))

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Trying to save quoataion items")
            quotation_items, quotation_total = self._get_quotation_items_and_total(quotation_id)
            cursor.executemany(get_quotation_items_insert_query(), quotation_items)
            _logger.info("evt=SEND_ORDER_TO_BETA msg=Quotation items saved")

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Generating job order number")
            job_order_number = self._generate_job_number(created_by, customer_id, quotation_id)
            self.job_order = job_order_number
            self.name = job_order_number

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Get Place of supply code from beta")
            cursor.execute(get_state_code_from_state_alpha_query(self.place_of_supply.code))

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Trying to create job order location")
            place_of_supply_code = cursor.fetchone()[0]
            cursor.execute(get_location_insert_query(), (job_order_number, place_of_supply_code))
            location_id = cursor.lastrowid
            _logger.info("evt=SEND_ORDER_TO_BETA msg=Location created with id" + str(location_id))

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Trying to create order")
            order_data = self._get_order_data(created_by, customer_id, quotation_id, quotation_total, job_order_number, place_of_supply_code, beta_bill_godown_id, beta_godown_id)
            cursor.execute(get_order_insert_query(), order_data)
            order_id = cursor.lastrowid
            _logger.info("evt=SEND_ORDER_TO_BETA msg=Order saved with id" + str(order_id))

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Updating quotation with order id")
            cursor.execute(get_update_quotation_with_order_query(), (order_id, quotation_id))

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Saving PO data")
            cursor.execute(get_order_po_insert_query(), (order_id, self.po_number, self.po_amount, self.po_amount))
            po_details = self._generate_po_details(order_id, quotation_items)

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Saving PO details")
            cursor.executemany(get_order_po_details_insert_query(), po_details)

            _logger.info("evt=SEND_ORDER_TO_BETA msg=Saving Bill Submission details")
            billing_process_data = self._get_billing_process_data(order_id, location_id)
            cursor.executemany(get_billing_process_insert_query(), billing_process_data)

            #IDK how to do it
            #cursor.execute(get_billing_process_insert_query, billing_process_data)
            """
            if self.env.user == self.env['crm.team'].search([('name', '=', 'INSIDE SALES')]).user_id:
                team_id = self.env['crm.team'].search([('name', 'in', ['INSIDE SALES', 'PAM'])]).ids
                return [('id', 'in', team_id)]
            else:
                team_id = self.env['crm.team'].search([('name', 'in', ['INSIDE SALES'])]).ids
                return [('id', 'in', team_id)]
            """
            # To be done if auto approval
            # DB::insert("INSERT INTO `order_item_feed`(`job_order`, `item_code`, `quantity`) VALUES (?, ?, ?)", [ $order->job_order, $order_item->item_code, $order_item->quantity]);

            super(SaleOrderInherit, self).action_confirm()
            cursor.close()
            connection.commit()

        except Error as e:
            _logger.error("evt=SEND_ORDER_TO_BETA msg=Houston, we have a %s", "major problem", exc_info=1)
            raise e

    def _get_billing_process_data(self, order_id, location_id):
        billing_process_data = {
            'order_id': order_id,
            'odoo_site_contact': self.bill_site_contact.id,
            'odoo_office_contact': self.bill_office_contact.id,
            'bill_submission_location': location_id,
            'site_address': self._concatenate_address_string([
                self.delivery_street,
                self.delivery_street2,
                self.delivery_city,
                self.delivery_state_id if self.delivery_state_id.name else False]),
            'site_pincode': self.delivery_zip,
            'office_address': self._concatenate_address_string( [
                self.bill_submission_office_branch.street,
                self.bill_submission_office_branch.street2,
                self.bill_submission_office_branch.city,
                self.bill_submission_office_branch.state_id if self.bill_submission_office_branch.state_id.name else False]),
            'office_pincode': self.bill_submission_office_branch.zip,
            'process': self.partner_id.bill_submission_process.name
        }
        return billing_process_data

    def _generate_po_details(self, order_id, quotation_items):
        po_details = []
        for item in quotation_items:
            po_details.append({
                'order_id': order_id,
                'po_no': self.po_number,
                'po_date': self.po_date.strftime('%Y-%m-%d'),
                'po_amount': self.po_amount,
                'item_code': item['item_code'],
                'quantity': item['quantity'],
            })
        return po_details

    def _get_quotation_items_and_total(self, quotation_id):
        quotation_items = []
        quotation_total = 0
        for order_line in self.order_line:
            quotation_items.append({
                'quotation_id': quotation_id,
                'item_code': order_line.product_id.default_code,
                'unit_price': order_line.price_unit,
                'quantity': order_line.product_uom_qty
            })
            quotation_total = quotation_total + (order_line.price_unit * order_line.product_uom_qty)
        return quotation_items, quotation_total

    def _validate_order_before_confirming(self):
        if self.tentative_quo:
            raise ValidationError(_("Confirmation of tentative quotation is not allowed"))
        if not self.po_number:
            raise ValidationError(_('PO Number is mandatory for confirming a quotation'))
        if not self.po_amount:
            raise ValidationError(_('PO Amount is mandatory for confirming a quotation'))
        if not self.po_date:
            raise ValidationError(_('PO Date is mandatory for confirming a quotation'))
        if not self.place_of_supply:
            raise ValidationError(_('Place of Supply is mandatory for confirming a quotation'))
        if not self.rental_order and self.customer_branch.rental_order is True:
            raise ValidationError(_('Rental Order is mandatory for this customer'))
        if not self.rental_advance and self.customer_branch.rental_advance is True:
            raise ValidationError(_('Rental Advance is mandatory for this customer'))
        if not self.security_cheque and self.customer_branch.security_cheque is True:
            raise ValidationError(_('Security Cheque is mandatory for this customer'))
        if not self.partner_id.vat:
            raise ValidationError(_("This customer does not have a PAN. Please check customer details"))
        if not self.partner_id.bill_submission_process:
            raise ValidationError(_("This customer does not have a Bill submission process defined. Please check customer details"))
        if self.partner_id.bill_submission_process.code == 'email' and not self.bill_submission_email:
            raise ValidationError(_("Bill submission email is required."))
        if self.partner_id.bill_submission_process.code in ['site', 'site_office'] and not self.site_bill_submission_godown :
            raise ValidationError(_("Site Bill submission godown is required."))
        if self.partner_id.bill_submission_process.code in ['site', 'site_office'] and not self.office_bill_submission_godown :
            raise ValidationError(_("Office Bill submission godown is required."))
        if self.partner_id.bill_submission_process.code in ['site', 'site_office'] and not self.bill_site_contact:
            raise ValidationError(_("Bill Site Contact is required."))
        if self.partner_id.bill_submission_process.code in ['office', 'site_office'] and not self.bill_office_contact:
            raise ValidationError(_("Customer Bill Submission Office Contac"))
        if self.partner_id.bill_submission_process.code in ['office', 'site_office'] and not self.bill_submission_office_branch:
            raise ValidationError(_("Bill Submission Office Branch is required."))

    def _generate_job_number(self, created_by, customer_id, quotation_id):
        today = datetime.date.today()
        job_order_number = str(today.year) + "/" + today.strftime("%b") + "/" + self.jobsite_id.name + "/" + str(created_by) + "/" + str(customer_id) + "/" + self.po_number + "/" + str(quotation_id)
        return job_order_number

    def _get_order_data(self, created_by, customer_id, quotation_id, quotation_total, job_order_number, place_of_supply_code,beta_bill_godown_id,  beta_godown_id):
        return {
            'quotation_id': quotation_id,
            'customer_id': customer_id,
            'job_order': job_order_number,
            'po_no': self.po_number,
            'place_of_supply': place_of_supply_code,
            'gstn': self.customer_branch.gstn,
            'security_cheque': self._get_document_if_exists('security_cheque'),
            'rental_advance': self._get_document_if_exists('rental_advance'),
            'rental_order': self._get_document_if_exists('rental_order'),
            'godown_id': beta_godown_id,
            'freight_amount': self.freight_amount,
            'billing_godown': beta_bill_godown_id,
            'created_by': created_by,
            'total': quotation_total,

        }

    def _get_document_if_exists(self, field_name):
        PREFIX = "s3://"
        attachment = self.env['ir.attachment'].sudo().search([('res_model', '=', 'sale.order'), ('res_field', '=', field_name), ('res_id', '=', self.id)])

        fname = attachment.store_fname if attachment else ""
        mimetype = attachment.mimetype if attachment else ""

        extension = mimetypes.guess_extension(mimetype, strict=True)

        if fname.startswith(PREFIX):
            return fname[len(PREFIX):] + extension if extension else ""

        return None

    def get_quotation_data(self, created_by, customer_id, beta_godown_id):
        return {
            'created_by': created_by,
            'customer_id': customer_id,
            'contact_name': self.purchaser_name.name,
            'phone_number': self.purchaser_name.mobile,
            'site_name': self.jobsite_id.name,
            'price_type': self.price_type,
            'total': 0.0,
            'freight': self.freight_amount,
            'gstn': 'Gstn Moved to Order',
            'billing_address_line': self._concatenate_address_string(
                [self.billing_street, self.billing_street2, self.billing_city]),
            'billing_address_city': self.billing_state_id.name if self.billing_state_id else "",
            'billing_address_pincode': self.billing_zip,
            'delivery_address_line': self._concatenate_address_string(
                [self.delivery_street, self.delivery_street2, self.delivery_city]),
            'delivery_address_city': self.delivery_state_id.name if self.delivery_state_id else "",
            'delivery_address_pincode': self.delivery_zip,
            'delivery_date': self.delivery_date.strftime('%Y-%m-%d'),
            'pickup_date': self.pickup_date.strftime('%Y-%m-%d'),
            'security_amt': self.security_amount if self.security_amount else 0.0,
            'freight_payment': self.freight_paid_by,
            'godown_id': beta_godown_id,
            'sign_type': 'MANUAL',
            'crm_account_id': self.id,
        }

    def _concatenate_address_string(self, address_strings):
        arr = [x for x in address_strings if x]
        return ', '.join(map(str, arr))

    def _get_connection(self):
        connection = False
        cursor = False
        try:
            beta_db_url = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_url')
            beta_db_port = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_port')
            beta_db = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db')
            beta_db_username = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_username')
            beta_db_password = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_password')

            if not (beta_db_url or beta_db_port or beta_db or beta_db_username  or beta_db_password):
                raise UserError("Beta Database is not configured. Please as system admins to configure it")

            connection = mysql.connector.connect(
                host=beta_db_url,
                port=beta_db_port,
                user=beta_db_username,
                password=beta_db_password,
                database=beta_db
            )
            return connection
        except Error as e:
            _logger.error("Error while connecting to MySQL using Connection pool ", e)
            raise e

    def _execute_single_update(self, statement, args):
        connection = False
        cursor = False
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            cursor.execute(statement, args)
        except Error as e:
            raise UserError(_("Could not perform selection action: " + str(e)))
        except UserError as e:
            raise e
        except Exception as e:
            raise UserError(_("Could not perform selection action: " + str(e)))
        finally:
            if connection and connection.is_connected() and cursor:
                cursor.close()