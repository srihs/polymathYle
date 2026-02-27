from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from .models import PaymentTier


@login_required
@staff_member_required
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
@staff_member_required
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
@staff_member_required
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
