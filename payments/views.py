import csv
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.utils import timezone

from .application_payments import PaymentError, RATE_PER_APPLICATION, payable_summary, process_payment, uploads
from .models import ApplicationPaymentRun, PaymentTier


@login_required
@permission_required('payments.view_paymenttier', raise_exception=True)
def payment_tier_list_view(request):
    """
    List all payment tiers with filtering options.
    Accessible only to staff members.
    """
    # Get all payment tiers
    tiers = PaymentTier.objects.all()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        tiers = tiers.filter(
            Q(name__icontains=search_query)
        )

    # Filter by payment type
    payment_type = request.GET.get('payment_type', '')
    if payment_type:
        tiers = tiers.filter(payment_type=payment_type)

    # Filter by active status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        tiers = tiers.filter(is_active=True)
    elif status_filter == 'inactive':
        tiers = tiers.filter(is_active=False)

    # Sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by in ['name', '-name', 'payment_type', '-payment_type', 'created_at', '-created_at']:
        tiers = tiers.order_by(sort_by)

    # Pagination
    paginator = Paginator(tiers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'tiers': page_obj.object_list,
        'payment_tiers': page_obj.object_list,  # Alias for template compatibility
        'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
        'search_query': search_query,
        'selected_payment_type': payment_type,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_count': tiers.count(),
    }

    return render(request, 'payments/payment_tier_list.html', context)


@login_required
@permission_required('payments.add_paymenttier', raise_exception=True)
def payment_tier_add_view(request):
    """
    Add a new payment tier.
    Accessible only to staff members.
    """
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        payment_type = request.POST.get('payment_type', '')
        hourly_rate = request.POST.get('hourly_rate', '').strip() or None
        fixed_amount = request.POST.get('fixed_amount', '').strip() or None
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not name or not payment_type:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'payments/payment_tier_form.html', {
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })

        try:
            # Create payment tier
            tier = PaymentTier(
                name=name,
                payment_type=payment_type,
                hourly_rate=hourly_rate if hourly_rate else None,
                fixed_amount=fixed_amount if fixed_amount else None,
                is_active=is_active,
            )
            tier.save()  # This will call full_clean() and validate

            messages.success(request, f'Payment tier "{tier.name}" added successfully!')
            return redirect('payment_tier_list')

        except ValidationError as e:
            # Display validation errors
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return render(request, 'payments/payment_tier_form.html', {
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })
        except Exception as e:
            messages.error(request, f'Error creating payment tier: {str(e)}')
            return render(request, 'payments/payment_tier_form.html', {
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })

    context = {
        'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
    }

    return render(request, 'payments/payment_tier_form.html', context)


@login_required
@permission_required('payments.change_paymenttier', raise_exception=True)
def payment_tier_edit_view(request, pk):
    """
    Edit an existing payment tier.
    Accessible only to staff members.
    """
    tier = get_object_or_404(PaymentTier, pk=pk)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        payment_type = request.POST.get('payment_type', '')
        hourly_rate = request.POST.get('hourly_rate', '').strip() or None
        fixed_amount = request.POST.get('fixed_amount', '').strip() or None
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not name or not payment_type:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'payments/payment_tier_form.html', {
                'tier': tier,
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })

        try:
            # Update payment tier
            tier.name = name
            tier.payment_type = payment_type
            tier.hourly_rate = hourly_rate if hourly_rate else None
            tier.fixed_amount = fixed_amount if fixed_amount else None
            tier.is_active = is_active
            tier.save()  # This will call full_clean() and validate

            messages.success(request, f'Payment tier "{tier.name}" updated successfully!')
            return redirect('payment_tier_list')

        except ValidationError as e:
            # Display validation errors
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return render(request, 'payments/payment_tier_form.html', {
                'tier': tier,
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })
        except Exception as e:
            messages.error(request, f'Error updating payment tier: {str(e)}')
            return render(request, 'payments/payment_tier_form.html', {
                'tier': tier,
                'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
                'form_data': request.POST,
            })

    context = {
        'tier': tier,
        'payment_types': PaymentTier.PAYMENT_TYPE_CHOICES,
    }

    return render(request, 'payments/payment_tier_form.html', context)


# ============== APPLICATION UPLOAD PAYMENTS ==============
# Uploaders are paid per scanned application. Like the upload log itself, these pages
# are superuser only.

def _require_superuser(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date() if value else None
    except ValueError:
        return None


@login_required
def application_payment_process_view(request):
    """Pay for every unpaid upload in the chosen dates, then show the payment."""
    _require_superuser(request)
    if request.method != 'POST':
        return redirect('application_payment_report')

    date_from = _parse_date(request.POST.get('date_from', ''))
    date_to = _parse_date(request.POST.get('date_to', ''))
    try:
        run = process_payment(date_from, date_to, request.user, request.POST.get('note', ''))
    except PaymentError as e:
        messages.error(request, str(e))
        return redirect(request.POST.get('next') or 'application_upload_log')

    messages.success(
        request,
        f'Payment processed: {run.total_applications} application'
        f'{"" if run.total_applications == 1 else "s"} for Rs. {run.total_amount:,.2f}.'
    )
    return redirect('application_payment_detail', run_id=run.id)


@login_required
def application_payment_report_view(request):
    """Processed payments, newest first, with what is still unpaid."""
    _require_superuser(request)

    runs = ApplicationPaymentRun.objects.select_related('processed_by').prefetch_related('lines__user')
    page_obj = Paginator(runs, 10).get_page(request.GET.get('page'))
    totals = runs.aggregate(applications=Sum('total_applications'), amount=Sum('total_amount'))
    unpaid = payable_summary()

    return render(request, 'payments/application_payment_report.html', {
        'page_obj': page_obj,
        'runs': page_obj.object_list,
        'paid_applications': totals['applications'] or 0,
        'paid_amount': totals['amount'] or 0,
        'unpaid': unpaid,
        'unpaid_applications': sum(row['applications'] for row in unpaid),
        'unpaid_amount': sum(row['amount'] for row in unpaid),
        'rate': RATE_PER_APPLICATION,
        'today': timezone.localdate(),
    })


@login_required
def application_payment_detail_view(request, run_id):
    """One payment: what each user was paid, and the applications it covered."""
    _require_superuser(request)
    run = get_object_or_404(
        ApplicationPaymentRun.objects.select_related('processed_by').prefetch_related('lines__user'), id=run_id
    )
    applications = run.applications.select_related('uploaded_by').order_by('uploaded_by__username', 'created_at')

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="application_payment_{run.id}.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([f'Payment {run.id}', f'{run.date_from} to {run.date_to}', f'Rate Rs. {run.rate}'])
        writer.writerow([])
        writer.writerow(['User', 'Applications', 'Amount (Rs.)', 'First Upload', 'Last Upload'])
        for line in run.lines.all():
            writer.writerow([
                (line.user.get_full_name() or line.user.username) if line.user else 'Not recorded',
                line.applications, f'{line.amount:.2f}', line.first_upload or '', line.last_upload or '',
            ])
        writer.writerow(['Total', run.total_applications, f'{run.total_amount:.2f}', '', ''])
        writer.writerow([])
        writer.writerow(['Uploaded At', 'Uploaded By', 'Reference Number', 'Student Name'])
        for app in applications:
            uploader = app.uploaded_by
            writer.writerow([
                timezone.localtime(app.created_at).strftime('%Y-%m-%d %H:%M'),
                (uploader.get_full_name() or uploader.username) if uploader else 'Not recorded',
                app.reference_number or '', app.full_name,
            ])
        return response

    return render(request, 'payments/application_payment_detail.html', {
        'run': run,
        'applications': applications,
    })
