from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from unittest.mock import patch, MagicMock
from accounts.models import User, BusinessProfile
from products.models import Product, Category
from channels_integration.models import Channel, ProductListing
from accounts.plans import get_limits, can_add_product, can_add_channel, channel_can_sync, discounts_enabled


class PlanGatingRemovalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        self.business = BusinessProfile.objects.create(
            user=self.user,
            business_name='Test Business',
            slug='test-business',
            plan='free',
            unlimited_access=False
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_plan_helpers_always_return_unrestricted(self):
        self.assertEqual(get_limits(self.business), {
            'max_products': None,
            'max_channels': None,
            'max_synced_channels': None,
            'discounts_enabled': True
        })
        self.assertTrue(can_add_product(self.business))
        self.assertTrue(can_add_channel(self.business))
        
        channel = Channel.objects.create(
            business=self.business,
            name='Test Channel',
            platform_type='whatsapp',
            connection_status='connected'
        )
        self.assertTrue(channel_can_sync(channel))
        self.assertTrue(discounts_enabled(self.business))

    def test_discounts_view_accessible_for_free_plan(self):
        response = self.client.get(reverse('discounts_view'))
        self.assertEqual(response.status_code, 200)

    def test_publish_product_gating_removed(self):
        category = Category.objects.create(business=self.business, name='Test Cat', slug='test-cat')
        product = Product.objects.create(
            business=self.business,
            category=category,
            title='Test Product',
            price=10.00,
            stock=5
        )
        ch1 = Channel.objects.create(business=self.business, name='Ch 1', platform_type='custom', connection_status='connected')
        ch2 = Channel.objects.create(business=self.business, name='Ch 2', platform_type='custom', connection_status='connected')

        response = self.client.get(reverse('publish_product', kwargs={'product_id': product.id}))
        self.assertEqual(response.status_code, 302)
        
        listings = ProductListing.objects.filter(product=product)
        self.assertEqual(listings.count(), 2)

    def test_product_edit_unpublished_shows_info_message(self):
        category = Category.objects.create(business=self.business, name='Test Cat', slug='test-cat')
        product = Product.objects.create(
            business=self.business,
            category=category,
            title='Unpublished Product',
            price=15.00,
            stock=10
        )
        
        response = self.client.post(
            reverse('product_edit', kwargs={'pk': product.id}),
            {
                'title': 'Updated Title',
                'description': 'Updated Desc',
                'price': '20.00',
                'stock': '10',
                'is_active': 'true',
                'category': str(category.id)
            },
            follow=True
        )
        
        messages = [m.message for m in get_messages(response.context['request'])]
        self.assertIn(
            "This product isn't published to any channel yet — use Publish from the product list or Channel Listings page first.",
            messages
        )
        self.assertEqual(ProductListing.objects.filter(product=product).count(), 0)

    @patch('channels_integration.whatsapp_client.requests.get')
    @patch('channels_integration.whatsapp_client.requests.post')
    def test_whatsapp_client_handles_plural_and_polling_fallback(self, mock_post, mock_get):
        from channels_integration.whatsapp_client import sync_product_to_whatsapp

        category = Category.objects.create(business=self.business, name='Cat', slug='cat')
        product = Product.objects.create(
            business=self.business,
            category=category,
            title='WA Product',
            price=50.00,
            stock=2,
            image='products/test.jpg'
        )
        channel = Channel.objects.create(
            business=self.business,
            name='WA Channel',
            platform_type='whatsapp',
            api_credentials={
                'phone_number_id': '12345',
                'access_token': 'token123',
                'catalog_id': 'cat123'
            }
        )

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {'handles': ['h_batch_99']}
        mock_post.return_value = mock_post_resp

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {'data': [{'handle': 'h_batch_99', 'status': 'FINISHED', 'errors': []}]}
        mock_get.return_value = mock_get_resp

        res = sync_product_to_whatsapp(product, channel, method='CREATE')
        self.assertTrue(res['success'])
        self.assertEqual(res['retailer_id'], f'ECOMORBIT-{product.id}')
