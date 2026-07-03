"""
Business service responsible for synchronizing products
across all connected sales channels.
"""

from typing import Dict, List

from .models import Channel
from . import facebook


def sync_all_channels(product) -> List[Dict]:
    """
    Synchronize a product across all active channels
    belonging to the product's business.

    Parameters
    ----------
    product : Product
        Product instance whose inventory/details changed.

    Returns
    -------
    list
        Synchronization results for each channel.
    """

    if product.business is None:
        return [
            {
                "status": "failed",
                "message": "Product is not linked to any business."
            }
        ]

    channels = (
        Channel.objects
        .filter(
            business=product.business,
            is_active=True,
        )
        .order_by("name")
    )

    results = []

    for channel in channels:

        try:

            if channel.platform_type == "facebook":

                response = facebook.sync_inventory(
                    product=product,
                    channel=channel,
                )

            # Future Integrations
            #
            # elif channel.platform_type == "instagram":
            #     response = instagram.sync_inventory(...)
            #
            # elif channel.platform_type == "google":
            #     response = google.sync_inventory(...)

            else:

                response = {
                    "status": "skipped",
                    "message": f"{channel.platform_type} integration not implemented."
                }

            results.append({

                "channel": channel.name,

                "platform": channel.platform_type,

                "result": response

            })

        except Exception as exc:

            results.append({

                "channel": channel.name,

                "platform": channel.platform_type,

                "result": {
                    "status": "failed",
                    "message": str(exc)
                }

            })

    return results