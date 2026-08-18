PLAN_LIMITS = {
    'free':       {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
    'starter':    {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
    'pro':        {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
    'enterprise': {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True},
}


def get_limits(business=None):
    return {'max_products': None, 'max_channels': None, 'max_synced_channels': None, 'discounts_enabled': True}


def can_add_product(business=None):
    return True


def can_add_channel(business=None):
    return True


def channel_can_sync(channel=None):
    return True


def discounts_enabled(business=None):
    return True