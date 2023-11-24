# -*- coding: utf-8 -*-

from odoo import models, _

import logging, requests, json
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def _concatenate_address_string(address_strings):
    arr = [x for x in address_strings if x]
    return ', '.join(map(str, arr))

class CustomerToBeta(models.TransientModel):
    _name = 'customer.to.beta'
    _description = 'Save Customer to Beta'

    def _get_branch_data_for_saving_in_beta(self, branch, user_id, customer_master_id):
        branch_data = {
            "odoo_branch_id": branch.id,
            "company": branch.name,
            "gstn": branch.gstn,
            "email": branch.email,
            "first_name":branch.branch_contact_name,
            "phone_number": branch.phone,
            "mobile": branch.mobile,
            "user_id": user_id,
            "bde": branch.bde.email,
            "branch_contact_name": branch.branch_contact_name,
            "billing_address_line": _concatenate_address_string(
                [branch.street, branch.street2, branch.state_id.name if branch.state_id else False]),
            "billing_address_city": branch.city,
            "billing_address_pincode": branch.zip,
            "mailing_address_line": _concatenate_address_string([branch.mailing_street, branch.mailing_street2,
                                                                 branch.mailing_state_id.name if branch.mailing_state_id else False]),
            "mailing_address_city": branch.mailing_city,
            "mailing_address_pincode": branch.mailing_zip
        }

        if customer_master_id:
            branch_data["master_id"] = customer_master_id

        return branch_data

    def _get_gst_customer_payload(self, branches, due_days, master_customer, user_id):
        payload = json.dumps({
            "partner": [
                {
                    "id": master_customer.id,
                    "is_non_gst": master_customer.is_non_gst_customer,
                    "name": master_customer.name,
                    "vat": master_customer.vat,
                    "email": master_customer.email,
                    "phone": master_customer.phone,
                    "street": master_customer.street,
                    "street2": master_customer.street2,
                    "city": master_customer.city,
                    "zip": master_customer.zip,
                    "business_type": master_customer.business_type.name,
                    "is_company": master_customer.is_company,
                    "rental_advance": master_customer.rental_advance,
                    "rental_order": master_customer.rental_order,
                    "security_cheque": master_customer.security_cheque,
                    "user_id": user_id,
                    "account_receivable": master_customer.account_receivable.email,
                    "credit_limit": master_customer.credit_limit,
                    "credit_rating": master_customer.credit_rating,
                    "days_due": False if not due_days else str(due_days),
                    "billing_process": master_customer.bill_submission_process.name

                }
            ],
            "branches": branches
        })
        return payload

    def _get_non_gst_customer_payload(self, branches, due_days, master_customer, user_id):
        payload = json.dumps({
            "partner": [
                {
                    'id': master_customer.id,
                    'company' : master_customer.name,
                    'pan': master_customer.vat,
                    'first_name' : False,
                    'last_name' : False,
                    'business_type' : False,
                    'phone_number' : master_customer.phone,
                    'email' : master_customer.email,
                    'purchase_firstname' : False,
                    'purchase_lastname' : False,
                    'purchase_email' : False,
                    'purchase_phone_number' : False,
                    'billing_address_line' : False,
                    'user_id': user_id,
                    'account_receivable': master_customer.account_receivable.email,
                    'billing_address_city' : "",
                    'billing_address_pincode' : "",
                    'billing_address_state': str(master_customer.state_id.code + "|" + master_customer.state_id.name),
                    'mailing_address_line' : _concatenate_address_string([master_customer.street , master_customer.street2]),
                    'mailing_address_city' : master_customer.city if master_customer.city else "",
                    'mailing_address_pincode' : master_customer.zip,
                    'mailing_address_state': str(master_customer.state_id.code + "|" + master_customer.state_id.name),
                    'security_letter' : master_customer.security_cheque,
                    'rental_advance' : master_customer.rental_advance,
                    'rental_order' : master_customer.rental_order,
                    'security_cheque' : master_customer.security_cheque,
                    'billing_process': master_customer.bill_submission_process.name,
                    'is_non_gst': master_customer.is_non_gst_customer,
                }
            ],
            "branches": branches

        })
        return payload

    def _get_customer_creation_endpoint(self):
        beta_customer_save_endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'ym_beta_updates.beta_customer_save_endpoint')
        if not beta_customer_save_endpoint:
            raise UserError(_("Beta save customer endpoint is not configured. Please reach out to system admins."))
        return beta_customer_save_endpoint
    def _create_customer_in_beta_if_not_exists(self, res_partner):
        try:
            master_customer = res_partner
            if not master_customer.in_beta:
                user_id = master_customer.user_id.login
                if master_customer.team_id.name == 'INSIDE SALES':
                    user_id = "customercare@youngman.co.in"

                branches = []
                for branch in master_customer.branch_ids:
                    branch_data = self._get_branch_data_for_saving_in_beta(branch, user_id, None)
                    branches.append(branch_data)

                payment_terms = master_customer.property_payment_term_id.name if master_customer.property_payment_term_id else None

                if not payment_terms or 'Immediate' in payment_terms:
                    due_days = 0
                elif '2 Months' in payment_terms:
                    due_days = 60
                else:
                    due_days = [int(i) for i in payment_terms.split() if i.isdigit()][0]

                payload = self._get_non_gst_customer_payload(branches, due_days, master_customer,
                                                             user_id) if master_customer.is_non_gst_customer else self._get_gst_customer_payload(
                    branches, due_days, master_customer, user_id)

                beta_customer_save_endpoint = self._get_customer_creation_endpoint()

                response = requests.request("POST", beta_customer_save_endpoint,
                                            headers={'Content-Type': 'application/json'}, data=payload, verify=False)
                response.raise_for_status()

                if not response.ok:
                    raise UserError(_("Unable to save customer in beta."))
                else:
                    master_customer.in_beta = True
                    for branch in master_customer.branch_ids:
                        branch.in_beta = True

        except requests.exceptions.HTTPError as errh:
            raise UserError("Http Error:" + str(errh))
        except requests.exceptions.ConnectionError as errc:
            raise UserError("Error Connecting:" + str(errc))
        except requests.exceptions.Timeout as errt:
            raise UserError("Timeout Error:" + str(errt))
        except requests.exceptions.RequestException as err:
            raise UserError("OOps:" + str(err))
        except Exception as e:
            raise UserError(str(e))