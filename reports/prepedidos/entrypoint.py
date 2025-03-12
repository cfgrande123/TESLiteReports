# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, CloudBlue
# All rights reserved.
#


from connect.client import R

from ..utils import convert_to_datetime, get_req_parameter, get_basic_value, get_value, today_str
from datetime import datetime, timedelta
HEADERS = (
    'Subscription ID', 'Subscription External ID', 'Vendor primary key',
    'Subscription Type', 'Creation date', 'Updated date', 'Status', 'Billing Period',
    'Anniversary Day', 'Anniversary Month', 'Contract ID', 'Contract Name',
    'Customer ID', 'Customer Name', 'Customer External ID',
    'Tax ID', 'KD',	'Bitdefender ID', 'Fractalia ID', 'Tier 1 Name', 'Tier 1 External ID',
    'Vendor Account ID', 'Vendor Account Name',
    'Product ID', 'Product Name', 'Email',
)
def generate(
    client=None,
    parameters=None,
    progress_callback=None,
    renderer_type=None,
    extra_context_callback=None,
):
    requests = _get_requests(client, parameters)
    progress = 0
    total = requests.count()
    if renderer_type == 'csv':
        yield HEADERS
        progress += 1
        total += 1
        progress_callback(progress, total)

    for request in requests:
        connection = request['asset']['connection']
        
        if renderer_type == 'json':
            yield {
                HEADERS[idx].replace(' ', '_').lower(): value
                for idx, value in enumerate(_process_line(request, connection))
            }
        else:
            yield _process_line(request, connection)
        progress += 1
        progress_callback(progress, total)


def _get_requests(client, parameters):
    query = R()
    today = datetime.utcnow()
    launch_date=datetime(2024, 9, 1, 0, 0, 00, 00000)
    all_status = ['pending', 'approved', 'failed']
   
    if parameters.get('date') and parameters['date']['before'] != '':       
        query &= R().created.lt(parameters['date']['before'])
    query &= R().created.gt(launch_date)
    query &= R().asset.product.id.eq("PRD-825-728-174")
    query &= R().status.oneof(all_status)
    query &= R().asset__connection__type.eq('production')
    query &= R().type.eq('purchase')
    
    return client.requests.filter(query).select(
        '-asset.items',
        '-asset.configuration',
        '-activation_key',
        '-template',
    )


def _process_line(request, connection):
    return (
        get_value(request, 'asset', 'id'),
        get_value(request, 'asset', 'external_id'),
        get_req_parameter(request,"subscriptionID"),
        get_value(request['asset'],'connection','type'), 
        convert_to_datetime(
            get_basic_value(request, 'created'),
        ), 
        convert_to_datetime(
            get_basic_value(request, 'updated'),
        ),
        get_value(request, 'asset', 'status'), 
        'monthly',
        '-', 
        '-',
        get_value(request['asset'], 'contract', 'id'),
        get_value(request['asset'], 'contract', 'name'),
        get_value(request['asset']['tiers'], 'customer', 'id'),
        get_value(request['asset']['tiers'], 'customer', 'name'),
        get_value(request['asset']['tiers'], 'customer', 'external_id'),
        get_value(request['asset']['tiers'],'customer','tax_id'),
        get_value(request['asset']['tiers']['customer']['contact_info'],'contact','first_name'),
        get_req_parameter(request,"subscriptionID"),
        get_req_parameter(request,"SubscriptionID_Fractalia"),
        get_value(request['asset']['tiers'], 'tier1', 'name'),
        get_value(request['asset']['tiers'], 'tier1', 'external_id'),
        get_value(request['asset']['tiers'], 'tier1', 'name'),
        get_value(request['asset']['tiers'], 'tier1', 'external_id'),
        get_value(request['asset'], 'product', 'id'),
        get_value(request['asset'], 'product', 'name'),
        get_value(request['asset']['tiers']['customer']['contact_info'],'contact','email'),
        
    )


