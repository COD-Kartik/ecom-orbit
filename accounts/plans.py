PLAN_LIMITS = {
    'free':       {'max_products': 15,  'max_channels': 1,    'max_synced_channels': 1,    'discounts_enabled': False},
    'starter':    {'max_products': 100, 'max_channels': 3,    'max_synced_channels': 2,    'discounts_enabled': False},
    'pro':        {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
    'enterprise': {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
}


def get_limits(business):
    if business.unlimited_access:
        return {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True}
    return PLAN_LIMITS.get(business.plan, PLAN_LIMITS['free'])


def can_add_product(business):
    limits = get_limits(business)
    if limits['max_products'] is None:
        return True
    return business.products.count() < limits['max_products']


def can_add_channel(business):
    limits = get_limits(business)
    if limits['max_channels'] is None:
        return True
    return business.channels.count() < limits['max_channels']


def channel_can_sync(channel):
    limits = get_limits(channel.business)
    if limits['max_synced_channels'] is None:
        return True
    synced_ids = list(
        channel.business.channels.order_by('created_at').values_list('id', flat=True)[:limits['max_synced_channels']]
    )
    return channel.id in synced_ids


def discounts_enabled(business):
    return get_limits(business)['discounts_enabled']