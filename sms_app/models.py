from django.db import models


class SMSMessage(models.Model):
    """One attempt to send an SMS, saved whether it succeeded or failed."""

    class Status(models.TextChoices):
        # Set by us when textbee never accepted the message
        # (missing credentials, invalid API key, network error, plan limit, ...).
        NOT_SUBMITTED = 'not_submitted', 'Not submitted'
        # Statuses reported by textbee for a submitted message.
        PENDING = 'pending', 'Pending'
        DISPATCHED = 'dispatched', 'Dispatched'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'

    provider = models.CharField(max_length=20, default='textbee')
    recipient = models.CharField(max_length=16, help_text='E.164 format, e.g. +639171234567')
    body = models.TextField(max_length=1600)
    # textbee's smsBatchId; empty when the message was never submitted.
    provider_message_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # User-friendly error text only; never raw provider responses or credentials.
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS message'
        verbose_name_plural = 'SMS messages'

    def __str__(self):
        return f'To {self.recipient} ({self.get_status_display()})'

    @property
    def is_submitted(self):
        """True if textbee accepted the message (it has a batch ID)."""
        return bool(self.provider_message_id)
