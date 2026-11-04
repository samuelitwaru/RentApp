from django.conf import settings
from django.db import models

from tenants.models import Tenant


class TenantAccessLink(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="access_links")
    token_hash = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="access_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Access link for {self.tenant.full_name} (expires {self.expires_at:%Y-%m-%d})"

    def is_valid(self):
        from django.utils import timezone

        return not self.revoked and self.expires_at > timezone.now()


class LinkRequest(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="link_requests")
    access_link = models.ForeignKey(
        TenantAccessLink, on_delete=models.SET_NULL, null=True, related_name="link_requests"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Link request from {self.tenant.full_name} at {self.requested_at:%Y-%m-%d %H:%M}"
