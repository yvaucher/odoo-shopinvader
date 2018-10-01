# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com)
# Benoît GUILLOT <benoit.guillot@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.addons.base_rest.components.service import to_int
from odoo.addons.component.core import Component
from odoo.exceptions import MissingError, UserError
from odoo.tools.translate import _


class ClaimService(Component):
    _inherit = 'base.shopinvader.service'
    _name = 'shopinvader.claim.service'
    _usage = 'claims'
    _expose_model = 'crm.claim'

    # The following method are 'public' and can be called from the controller.
    # All params are untrusted so please check it !

    def get(self, _id):
        return self._to_json(self._get(_id))[0]

    def search(self, **params):
        return self._paginate_search(**params)

    def create(self, params):
        claim = self.env['crm.claim'].create(self._prepare_claim(params))
        self.backend_record._send_notification('claim_confirmation', claim)
        # Choose the good one
        # return {'data': self._to_json(claim)}
        return self.search()

    def update(self, params):
        claim = self.env['crm.claim'].search([
            ('partner_id', '=', self.partner.id),
            ('shopinvader_backend_id', '=', self.backend_record.id),
            ('id', '=', params['id'])])
        if not claim:
            raise MissingError(_('Claim not found'))
        if params.get('add_message'):
            claim.message_post(
                body=params['add_message'],
                type='comment',
                subtype='mail.mt_comment',
                content_subtype='plaintext',
                author_id=self.partner.id)
        return {'data': self._to_json(claim)}

    def _validator_get(self):
        return {}

    def _validator_search(self):
        return {
            'id': {'coerce': to_int},
            'per_page': {
                'coerce': to_int,
                'nullable': True,
                },
            'page': {
                'coerce': to_int,
                'nullable': True,
                },
            'scope': {
                'type': 'dict',
                'nullable': True,
                },
        }

    # The following method are 'private' and should be never never NEVER call
    # from the controller.
    # All params are trusted as they have been checked before

    def _validator_create(self):
        return {
            'sale_order_line': {
                'type': 'list',
                'schema': {
                    'id': {'coerce': to_int, 'required': True},
                    'qty': {'coerce': to_int, 'nullable': True}
                    }
                },
            'message': {'type': 'string', 'required': True},
            'subject_id': {'coerce': to_int, 'required': True},
            }

    def _validator_update(self):
        return {
            'id': {'coerce': to_int, 'required': True},
            'add_message': {'type': 'string', 'required': True}
        }

    def _parser_partner(self):
        return ['id', 'display_name', 'ref']

    def _parser_stage(self):
        return ['id', 'name']

    def _json_parser(self):
        res = [
            'id',
            'name',
            'code',
            'create_date',
            ('stage_id', self._parser_stage()),
            ('claim_line_ids:lines', [
                ('product_id:product', ('id', 'name')),
                'product_returned_quantity:qty',
                ]),
            ('ref', ('id', 'name')),
        ]
        return res

    def _to_json(self, claims):
        res = []
        if not claims:
            return res
        for claim in claims:
            parsed_claim = claim.jsonify(self._json_parser())[0]
            parsed_claim['messages'] = []
            for message in claim.message_ids:
                if message.type != 'comment' or not message.subtype_id:
                    continue
                parsed_claim['messages'].append({
                    'body': message.body,
                    'date': message.date,
                    'author': message.author_id.display_name,
                    'email': message.author_id.email,
                    })
            parsed_claim['messages'].append({
                'body': claim.description,
                'date': claim.create_date,
                'author': claim.partner_id.name,
                'email': claim.partner_id.email,
                })
            parsed_claim['messages'].reverse()
            res.append(parsed_claim)
        return res

    def _prepare_claim(self, params):
        categ = self.env['crm.case.categ'].search(
            [('id', '=', params['subject_id'])])
        claim_type = self.env.ref('crm_claim_type.crm_claim_type_customer').id
        backend_id = self.backend_record.id
        vals = {
            'categ_id': params['subject_id'],
            'name': categ.name,
            'description': params['message'],
            'partner_id': self.partner.id,
            'claim_type': claim_type,
            'shopinvader_backend_id': backend_id,
            'claim_line_ids': []
        }
        vals = self.env['crm.claim'].play_onchanges(vals, ['partner_id'])
        order = False
        for line in params['sale_order_line']:
            if not line['qty']:
                continue
            so_line = self.env['sale.order.line'].search([
                ('id', '=', line['id']),
                ('order_id.partner_id', '=', self.partner.id),
                ('order_id.shopinvader_backend_id', '=', backend_id)
            ])
            if not so_line:
                raise MissingError(
                    _('The sale order line %s does not exist') % line['id'])
            if not order:
                order = so_line.order_id
                vals['ref'] = 'sale.order,%s' % order.id
            elif order != so_line.order_id:
                raise UserError(
                    _('All sale order lines must'
                      'come from the same sale order'))
            if order.invoice_ids and not vals.get('invoice_id', False):
                vals['invoice_id'] = order.invoice_ids[0].id
            vals['claim_line_ids'].append((0, 0, {
                'product_id': so_line.product_id.id,
                'product_returned_quantity': line['qty'],
                'claim_origin': 'none'}))
        if not vals['claim_line_ids']:
            raise UserError(_('You have to select an item'))
        return vals


class ClaimSubjectService(Component):
    _inherit = 'shopinvader.base.service'
    _name = 'shopinvader.crm.claim.category'
    _usage = 'claim'
    _expose_model = 'crm.claim.category'

    # The following method are 'public' and can be called from the controller.
    # All params are untrusted so please check it by using the decorator
    # secure params and the linked validator !

    def get(self, _id):
        categ = self._get(_id)
        return self._to_json(categ)[0]
    # The following method are 'private' and should be never never NEVER call
    # from the controller.
    # All params are trusted as they have been checked before

    def _validator_get(self):
        return {}

    def _validator_search(self):
        return {
            'id': {'coerce': to_int},
            'per_page': {
                'coerce': to_int,
                'nullable': True,
                },
            'page': {
                'coerce': to_int,
                'nullable': True,
                },
            'scope': {
                'type': 'dict',
                'nullable': True,
                },
        }

    def _json_parser(self):
        res = [
            'id',
            'name',
        ]
        return res

    def _to_json(self, subject):
        return subject.jsonify(self._json_parser())
