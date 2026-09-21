"""
Paying users for the applications they upload.

Rs. 100 is paid per uploaded (scanned) application. Staff pick a date range and process
the payment; every unpaid upload in that range is attached to the payment run, so the same
application is never paid for twice, even if a later range overlaps.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Min
from django.utils import timezone

# Fixed rate per uploaded application (Sri Lankan rupees)
RATE_PER_APPLICATION = Decimal('100.00')


class PaymentError(Exception):
    """Raised when a payment cannot be processed; the message is shown to the user."""


def uploads(date_from=None, date_to=None, unpaid_only=False):
    """Scanned applications, optionally limited to a date range (upload date) and unpaid ones."""
    from students.models import Application

    qs = Application.objects.filter(application_type='OFFLINE')
    if unpaid_only:
        qs = qs.filter(payment_run__isnull=True)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def payable_summary(date_from=None, date_to=None):
    """
    Per-user unpaid uploads for the range, most applications first. Each row:
    user, user_id, applications, amount, first_upload, last_upload.
    """
    rows = list(
        uploads(date_from, date_to, unpaid_only=True)
        .values('uploaded_by')
        .annotate(applications=Count('id'), first_upload=Min('created_at'), last_upload=Max('created_at'))
        .order_by('-applications')
    )
    users = {u.id: u for u in User.objects.filter(id__in=[r['uploaded_by'] for r in rows if r['uploaded_by']])}
    return [
        {
            'user': users.get(row['uploaded_by']),
            'user_id': row['uploaded_by'],
            'applications': row['applications'],
            'amount': RATE_PER_APPLICATION * row['applications'],
            'first_upload': timezone.localdate(row['first_upload']),
            'last_upload': timezone.localdate(row['last_upload']),
        }
        for row in rows
    ]


def process_payment(date_from, date_to, user, note=''):
    """
    Pay for every unpaid upload between the two dates (inclusive) and return the payment run.
    Raises PaymentError when the dates are missing or there is nothing left to pay for.
    """
    from students.models import Application

    from .models import ApplicationPaymentLine, ApplicationPaymentRun

    if not date_from or not date_to:
        raise PaymentError('Choose both a start and an end date for the payment.')
    if date_from > date_to:
        raise PaymentError('The start date must be on or before the end date.')

    with transaction.atomic():
        # Lock the rows so two people processing at once cannot pay for the same application
        pending = uploads(date_from, date_to, unpaid_only=True).select_for_update()
        ids = list(pending.values_list('id', flat=True))
        if not ids:
            raise PaymentError('There are no unpaid uploads between those dates.')

        lines = payable_summary(date_from, date_to)
        run = ApplicationPaymentRun.objects.create(
            date_from=date_from,
            date_to=date_to,
            rate=RATE_PER_APPLICATION,
            total_applications=len(ids),
            total_amount=RATE_PER_APPLICATION * len(ids),
            note=(note or '').strip(),
            processed_by=user if getattr(user, 'is_authenticated', False) else None,
        )
        ApplicationPaymentLine.objects.bulk_create([
            ApplicationPaymentLine(
                run=run, user_id=line['user_id'], applications=line['applications'],
                amount=line['amount'], first_upload=line['first_upload'], last_upload=line['last_upload'],
            )
            for line in lines
        ])
        Application.objects.filter(id__in=ids).update(payment_run=run)
    return run
