# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
import uuid
from odoo.addons.queue_job.job import job


class ShopinvaderPartner(models.Model):
    _inherit = 'shopinvader.partner'

    last_pwd_reset_datetime = fields.Datetime(
        'Last password reset date',
        help='date of the last password reset of the customer')
    last_reset_send_datetime = fields.Datetime(
        'Password reset send at',
        help='date of last password reset sent')
    nbr_reset = fields.Integer()

    def _send_reset_password_email(self, template_id, token):
        return self.env['mail.template'].with_context(token=token).browse(
            template_id).send_mail(self.id)

    @job(default_channel='root.shopinvader')
    def _reset_password(self, template_id, date_validity):
        self.ensure_one()
        self.write({
            'nbr_reset': (self.nbr_reset or 0) + 1,
            'last_reset_send_datetime': fields.datetime.now(),
            })
        token = uuid.uuid4().hex
        self._send_reset_password_email(template_id, token)
        with self.backend_id.work_on(self._name) as work:
            adapter = work.component(usage='backend.adapter')
            adapter.write(self.external_id, {
                '_auth_reset_token': token,
                '_auth_reset_sent_at': date_validity,
                })
            return 'Reset Password Sent'
