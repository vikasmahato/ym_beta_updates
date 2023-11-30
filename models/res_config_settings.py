# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    beta_db_url = fields.Char(string='Beta DB Url', config_parameter='ym_beta_updates.beta_db_url')
    endpoint = fields.Char(string='Beta DB Endpoint', config_parameter='ym_beta_updates.endpoint')
    beta_db_port = fields.Char(string='Beta DB Port', config_parameter='ym_beta_updates.beta_db_port')
    beta_db = fields.Char(string='Beta DB Name', config_parameter='ym_beta_updates.beta_db')
    beta_db_username = fields.Char(string='Beta DB Username', config_parameter='ym_beta_updates.beta_db_username')
    beta_db_password = fields.Char(string='Beta DB Password', config_parameter='ym_beta_updates.beta_db_password')
    beta_customer_save_endpoint = fields.Char(string='Customer Save Endpoint', config_parameter='ym_beta_updates.beta_customer_save_endpoint')
    beta_branch_save_endpoint = fields.Char(string='Branch Save Endpoint', config_parameter='ym_beta_updates.beta_branch_save_endpoint')
    file_save_bucket_url = fields.Char(string='File Save Bucket Url', config_parameter='ym_beta_updates.file_save_bucket_url')