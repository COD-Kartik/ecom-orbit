from .models import BusinessProfile
from django.utils.text import slugify

def save_user_role(backend, user, response, *args, **kwargs):
    """
    After Google login, if user has no role set,
    assign business_owner by default and create a BusinessProfile.
    """
    if backend.name == 'google-oauth2':
        # Set role if not already set
        if not user.role or user.role == '':
            user.role = 'business_owner'
            user.save()

        # Create BusinessProfile if doesn't exist
        if not BusinessProfile.objects.filter(user=user).exists():
            business_name = response.get('name', user.username)
            slug = slugify(business_name)
            original_slug = slug
            counter = 1
            while BusinessProfile.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1

            BusinessProfile.objects.create(
                user=user,
                business_name=business_name,
                slug=slug,
            )