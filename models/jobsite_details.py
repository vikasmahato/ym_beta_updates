from odoo import models, fields, api
import logging
import mysql.connector
from mysql.connector import Error
import json
import requests
import traceback

import datetime, mimetypes
import pytz

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError, ValidationError

from odoo.exceptions import UserError




class JobsiteDetails(models.Model):
    _inherit = 'jobsite'

    def update_running_order_count(self):
        self.running_order_count = self._fetch_running_order()

    def _fetch_running_order(self):
        select_site_name = self.site_name

        try:
            connection = self._get_connection()
            cursor = connection.cursor()

            orders = "SELECT js.site_name, COUNT(orders.job_order) AS Orders FROM orders INNER JOIN quotations q ON orders.id = q.order_id INNER JOIN job_site js ON q.site_name = js.site_name GROUP BY 1;"

            cursor.execute(orders)
            rows = cursor.fetchall()

            for row in rows:
                site_name = row[0]
                order_count = row[1]
                if site_name == select_site_name:
                    running_order_count = order_count
                    break

        except Error as e:
            raise UserError(_("Could not perform selection action: " + str(e)))
        except UserError as e:
            raise e
        except Exception as e:
            raise UserError(_("Could not perform selection action: " + str(e)))
        finally:
            if connection and connection.is_connected() and cursor:
                cursor.close()

        return running_order_count

    def _get_connection(self):
        connection = False
        cursor = False
        try:
            beta_db_url = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_url')
            beta_db_port = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_port')
            beta_db = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db')
            beta_db_username = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_username')
            beta_db_password = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_password')

            if not (beta_db_url or beta_db_port or beta_db or beta_db_username or beta_db_password):
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