# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, CloudBlue
# All rights reserved.
#

from connect.client import R

from ..utils import convert_to_datetime, get_sub_parameter, get_value,  get_basic_value
from datetime import datetime, timedelta

HEADERS = (
    'Subscription ID', 'Subscription External ID', 'Vendor primary key',
    'Subscription Type', 'Creation date', 'Updated date', 'Status', 'Billing Period',
    'Anniversary Day', 'Anniversary Month', 'Contract ID', 'Contract Name',
    'Customer ID', 'Customer Name', 'Customer External ID',
    'Tax ID', 'KD',	'Bitdefender ID', 'Fractalia ID', 'Tier 1 Name', 'Tier 1 External ID',
    'Vendor Account ID', 'Vendor Account Name',
    'Product ID', 'Product Name',
)

def generate(
    client=None,
    parameters=None,
    progress_callback=None,
    renderer_type=None,
    extra_context_callback=None,
):
    products_primary_keys = {}
    act_subscriptions = _get_active_subscriptions(client, parameters)
    term_subscriptions = _get_terminated_subscriptions(client, parameters)
    total = act_subscriptions.count()+term_subscriptions.count()
    progress = 0
    if renderer_type == 'csv':
        yield HEADERS
        progress += 1
        total += 1
        progress_callback(progress, total)

    for subscription in act_subscriptions:
        primary_vendor_key = get_sub_parameter(subscription,"subscriptionID")
        secondary_vendor_key =  get_sub_parameter(subscription,"SubscriptionID_Fractalia")
        if renderer_type == 'json':
            yield {
                HEADERS[idx].replace(' ', '_').lower(): value
                for idx, value in enumerate(_process_line(subscription, primary_vendor_key,secondary_vendor_key))
            }
        else:
            yield _process_line(subscription, primary_vendor_key,secondary_vendor_key)
        progress += 1
        progress_callback(progress, total)

    for subscription in term_subscriptions:
        primary_vendor_key =  get_sub_parameter(subscription,"subscriptionID")
        secondary_vendor_key =  get_sub_parameter(subscription,"SubscriptionID_Fractalia")
        if primary_vendor_key != secondary_vendor_key:
            if renderer_type == 'json':
                yield {
                    HEADERS[idx].replace(' ', '_').lower(): value
                    for idx, value in enumerate(_process_line(subscription, primary_vendor_key,secondary_vendor_key))
                }
            else:
                yield _process_line(subscription, primary_vendor_key,secondary_vendor_key)
        progress += 1
        progress_callback(progress, total)

def _get_active_subscriptions(client, parameters):
    today = datetime.utcnow()
    day_16_of_this_month = today.replace(day=16, month=today.month, year=today.year,minute=0, second=0, microsecond=0)
    query = R()
    query &= R().events.updated.at.lt(day_16_of_this_month)
    query &= R().product.id.eq("PRD-825-728-174")
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    if parameters.get('period') and parameters['period']['all'] is False:
        query &= R().billing.period.uom.oneof(parameters['period']['choices'])
    query &= R().status.oneof(['active'])
    query &= R().connection.type.eq('production')
    return client.ns('subscriptions').assets.filter(query)

def _get_rfs_date(subscription):
    for request in subscription['requests']
      if get_basic_value(request, 'type')=='purchase' 
         return get_basic_value(request,'updated')

def _get_terminated_subscriptions(client, parameters):
    query = R()
    # today = datetime.utcnow()
    # month, year = (today.month -1, today.year) if today.month != 1 else (12, today.year -1)
    # day_16_of_prev_month = today.replace(day=16, month=month, year=year,minute=0, second=0, microsecond=0)
    # query &= R().events.updated.at.ge(day_16_of_prev_month)
    query &= R().product.id.eq("PRD-825-728-174")
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    if parameters.get('period') and parameters['period']['all'] is False:
        query &= R().billing.period.uom.oneof(parameters['period']['choices'])
    query &= R().status.oneof(['terminated'])
    query &= R().connection.type.eq('production') 
    return client.ns('subscriptions').assets.filter(query)

def calculate_period(delta, uom):
    if delta == 1:
        if uom == 'monthly':
            return 'Monthly'
        return 'Yearly'
    else:
        if uom == 'monthly':
            return f'{int(delta)} Months'
        return f'{int(delta)} Years'


def get_anniversary_day(subscription_billing):
    if 'anniversary' in subscription_billing and 'day' in subscription_billing['anniversary']:
        return subscription_billing['anniversary']['day']
    return '-'


def get_anniversary_month(subscription_billing):
    if 'anniversary' in subscription_billing and 'month' in subscription_billing['anniversary']:
        return subscription_billing['anniversary']['month']
    return '-'


def search_product_primary(parameters):
    for param in parameters:
        if param['constraints'].get('reconciliation'):
            return param['name']


def get_primary_key(parameters, product_id, client, products_primary_keys):
    try:
        if product_id not in products_primary_keys:
            prod_parameters = client.collection(
                'products',
            )[product_id].collection(
                'parameters',
            ).all()
            primary_id = search_product_primary(prod_parameters)
            products_primary_keys[product_id] = primary_id
        for param in parameters:
            if param['id'] == products_primary_keys[product_id]:
                return param['value'] if 'value' in param and len(param['value']) > 0 else '-'
    except ClientError:
        pass
    return '-'


def _process_line(subscription, primary_vendor_key,secondary_vendor_key):
        
    return (
        subscription.get('id'),
        subscription.get('external_id', '-'),
        primary_vendor_key,
        get_value(subscription, 'connection', 'type'),
        convert_to_datetime(subscription['events']['created']['at']),
        convert_to_datetime(_get_rfs_date(subscription)),
        subscription.get('status'),
        calculate_period(
            subscription['billing']['period']['delta'],
            subscription['billing']['period']['uom'],
        ) if 'billing' in subscription else '-',
        get_anniversary_day(subscription['billing']) if 'billing' in subscription else '-',
        get_anniversary_month(subscription['billing']) if 'billing' in subscription else '-',
        subscription['contract']['id'] if 'contract' in subscription else '-',
        subscription['contract']['name'] if 'contract' in subscription else '-',
        get_value(subscription.get('tiers', ''), 'customer', 'id'),
        get_value(subscription.get('tiers', ''), 'customer', 'name'),
        get_value(subscription.get('tiers', ''), 'customer', 'external_id'),
        subscription["tiers"]["customer"]["tax_id"],
        subscription["tiers"]["customer"]["contact_info"]["contact"]["first_name"],
        primary_vendor_key,
        secondary_vendor_key,
        get_value(subscription.get('tiers', ''), 'tier1', 'name'),
        get_value(subscription.get('tiers', ''), 'tier1', 'external_id'),
        get_value(subscription['connection'], 'vendor', 'id'),
        get_value(subscription['connection'], 'vendor', 'name'),
        get_value(subscription, 'product', 'id'),
        get_value(subscription, 'product', 'name'),
    )
