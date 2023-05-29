from odoo import models, fields, api
import logging
import mysql.connector
from mysql.connector import Error

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError


class JobsiteDetails(models.Model):
    _inherit = 'jobsite'



    def fetch_running_order(self,values):
        select_site_name = values.name

        try:
            connection = self._get_connection()
            cursor = connection.cursor()

            query = """
                SELECT js.site_name, COUNT(orders.job_order) AS Orders
                FROM orders
                INNER JOIN quotations q ON orders.id = q.order_id
                INNER JOIN job_site js ON q.site_name = js.site_name
                WHERE orders.active=1 and js.site_name = %s;
            """
            cursor.execute(query, (select_site_name,))
            rows = cursor.fetchall()

            for row in rows:
                site_name = row[0]
                order_count = row[1]
                if site_name == select_site_name:
                    running_order_count = order_count
                    break
            else:
                running_order_count = 0  # Set a default value if no match found

        except Error as e:
            raise UserError("Error occurred during selection: %s" % str(e))
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        return running_order_count

    def _get_connection(self):
        try:
            beta_db_url = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_url')
            beta_db_port = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_port')
            beta_db = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db')
            beta_db_username = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_username')
            beta_db_password = self.env['ir.config_parameter'].sudo().get_param('ym_beta_updates.beta_db_password')

            if not all([beta_db_url, beta_db_port, beta_db, beta_db_username, beta_db_password]):
                raise UserError("Beta Database is not fully configured. Please ask system admins to configure it.")

            connection_config = {
                'host': beta_db_url,
                'port': beta_db_port,
                'user': beta_db_username,
                'password': beta_db_password,
                'database': beta_db
            }

            connection = mysql.connector.connect(**connection_config)
            return connection

        except Error as e:
            _logger.error("Error while connecting to MySQL using Connection pool: %s", e)
            raise UserError("Error occurred while connecting to the database: %s" % str(e))
