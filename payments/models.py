from django.db import models
from django.core.exceptions import ValidationError


class PaymentTier(models.Model):
    """
    Payment tier configuration for teacher compensation.
    Defines either hourly rates or fixed amounts based on payment type.
    """
    # Payment type choices
    PAYMENT_TYPE_CHOICES = [
        ('HOURLY', 'Hourly Rate'),
        ('FIXED', 'Fixed Amount'),
    ]

    # Basic info
    name = models.CharField(
        max_length=100,
        help_text="Tier name (e.g., 'Senior Teacher', 'Junior Teacher')"
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        help_text="Type of payment: hourly rate or fixed amount"
    )

    # Payment amounts (mutually exclusive based on payment_type)
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Hourly rate (used when payment_type is HOURLY)"
    )
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed amount (used when payment_type is FIXED)"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Payment Tier'
        verbose_name_plural = 'Payment Tiers'

    def __str__(self):
        if self.payment_type == 'HOURLY':
            return f"{self.name} - {self.hourly_rate}/hour"
        return f"{self.name} - {self.fixed_amount} (fixed)"

    def clean(self):
        """
        Validate that the correct payment field is set based on payment_type.
        """
        super().clean()

        if self.payment_type == 'HOURLY':
            if not self.hourly_rate:
                raise ValidationError({
                    'hourly_rate': 'Hourly rate is required when payment type is HOURLY.'
                })
            if self.fixed_amount:
                raise ValidationError({
                    'fixed_amount': 'Fixed amount should not be set when payment type is HOURLY.'
                })
        elif self.payment_type == 'FIXED':
            if not self.fixed_amount:
                raise ValidationError({
                    'fixed_amount': 'Fixed amount is required when payment type is FIXED.'
                })
            if self.hourly_rate:
                raise ValidationError({
                    'hourly_rate': 'Hourly rate should not be set when payment type is FIXED.'
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def display_amount(self):
        """Return the appropriate amount based on payment type."""
        if self.payment_type == 'HOURLY':
            return self.hourly_rate
        return self.fixed_amount
