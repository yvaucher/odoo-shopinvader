# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.addons.component.core import AbstractComponent


class BaseShopinvaderService(AbstractComponent):
    _inherit = 'base.rest.service'
    _name = 'base.shopinvader.service'
    _collection = 'locomotive.backend'

    @property
    def partner(self):
        return self.work.partner

    @property
    def shopinvader_session(self):
        return self.work.shopinvader_session

    @property
    def locomotive_backend(self):
        return self.work.locomotive_backend

    def to_domain(self, scope):
        if not scope:
            return []
        # Convert the liquid scope syntax to the odoo domain
        OPERATORS = {
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
            'ne': '!='}
        domain = []
        if scope:
            for key, value in scope.items():
                if '.' in key:
                    key, op = key.split('.')
                    op = OPERATORS[op]
                else:
                    op = '='
                domain.append((key, op, value))
        return domain

    def _paginate_search(
            self, model_name, default_page=1, default_per_page=5, **params):
        domain = self._get_base_search_domain()
        domain += params.get('domain', [])
        model_obj = self.env[model_name]
        total_count = model_obj.search_count(domain)
        page = params.get('page', default_page)
        per_page = params.get('per_page', default_per_page)
        records = model_obj.search(
            domain, limit=per_page, offset=per_page*(page-1))
        return {
            'size': total_count,
            'data': self._to_json(records),
            }

    def _get_base_search_domain():
        return []
