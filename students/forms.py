from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator
from .models import Application


def validate_upload_size(file):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise forms.ValidationError(f'File size must be less than {settings.MAX_UPLOAD_SIZE_MB}MB.')


class ApplicationForm(forms.ModelForm):
    """
    Online application form for Cambridge English Young Learners program
    """
    gender = forms.ChoiceField(
        choices=[('', 'Gender')] + Application.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Application
        fields = [
            'name_with_initials', 'full_name', 'date_of_birth', 'age', 'gender', 'nationality',
            'student_email', 'student_nic', 'current_school', 'siblings_info',
            'mother_name', 'mother_contact_number', 'mother_occupation',
            'father_name', 'father_contact_number', 'father_occupation',
            'home_address', 'whatsapp_number', 'primary_contact_email',
            'schedule_preferences', 'special_comments', 'terms_accepted',
            'application_form_scan',  # For scanned/uploaded application forms
            'document1', 'document1_type', 'document2', 'document2_type',
            'admission_number', 'application_date', 'receipt_number'  # Office Use fields
        ]

        labels = {
            'document1': 'Additional Document 1',
            'document1_type': 'Document 1 Type',
            'document2': 'Additional Document 2',
            'document2_type': 'Document 2 Type',
        }

        widgets = {
            'name_with_initials': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name with Initials'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control flatpickr-input',
                'placeholder': 'Date of Birth',
                'data-provider': 'flatpickr',
                'data-date-format': 'Y-m-d',
                'type': 'text'  # Override to text for flatpickr
            }, format='%Y-%m-%d'),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nationality'
            }),
            'student_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Student Email'
            }),
            'student_nic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Student NIC'
            }),
            'current_school': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current School'
            }),
            'siblings_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Siblings at Polymath'
            }),

            # Mother's Information
            'mother_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Mother's Name"
            }),
            'mother_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Mother's Contact Number"
            }),
            'mother_occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Mother's Occupation"
            }),

            # Father's Information
            'father_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Father's Name"
            }),
            'father_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Father's Contact Number"
            }),
            'father_occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Father's Occupation"
            }),

            # Contact Information
            'home_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Home Address'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'WhatsApp Number'
            }),
            'primary_contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Primary Contact Email'
            }),

            # Schedule Preferences
            'schedule_preferences': forms.HiddenInput(),

            # Special Comments
            'special_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional Information'
            }),

            # Terms
            'terms_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            # Scanned Application Form (for offline/upload submissions)
            'application_form_scan': forms.FileInput(attrs={
                'class': 'form-control d-none',
                'accept': 'image/*,.pdf'
            }),

            # Additional supporting documents (birth certificate, photo, etc.)
            'document1': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'document1_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'document2': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'document2_type': forms.Select(attrs={
                'class': 'form-select'
            }),

            # Office Use Only fields
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'admission_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., YLE-2025-001'
            }),
            'application_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Receipt Number'
            }),
        }

    def __init__(self, *args, require_backside=False, **kwargs):
        # Scanned (uploaded) applications must include the backside of the paper form
        self.require_backside = require_backside
        super().__init__(*args, **kwargs)
        # Scans and supporting documents may be PDFs or images
        for name in ('application_form_scan', 'document1', 'document2'):
            if name in self.fields:
                self.fields[name].validators += [
                    FileExtensionValidator(settings.ALLOWED_UPLOAD_EXTENSIONS),
                    validate_upload_size,
                ]

    def clean(self):
        cleaned_data = super().clean()
        if not self.require_backside:
            return cleaned_data

        backside = Application.BACKSIDE_DOCUMENT_TYPE
        has_backside = any(
            cleaned_data.get(file_field) and cleaned_data.get(type_field) == backside
            for file_field, type_field in (('document1', 'document1_type'), ('document2', 'document2_type'))
        )
        if not has_backside:
            raise forms.ValidationError(
                'Please upload the backside of the application as an additional document '
                'and set its type to "Backside of the Application".',
                code='backside_required',
            )
        both_backside = all(
            cleaned_data.get(type_field) == backside for type_field in ('document1_type', 'document2_type')
        )
        if both_backside:
            raise forms.ValidationError(
                'Only one additional document can be the backside of the application.',
                code='backside_duplicate',
            )
        return cleaned_data

    def clean_terms_accepted(self):
        """
        Ensure terms are accepted for online applications.
        For scanned/uploaded applications, terms acceptance is not required.
        """
        terms = self.cleaned_data.get('terms_accepted', False)

        # Check if this is from the upload form (which doesn't have terms checkbox)
        # by checking if the checkbox was in the initial POST data
        if 'terms_accepted' in self.data:
            # Terms checkbox was in the form, so validate it
            if not terms:
                raise forms.ValidationError('You must accept the terms and conditions to submit this application.')

        return terms

    def clean_admission_number(self):
        """Admission numbers must be unique across applications and students (ignoring case and spacing)."""
        number = Application.normalize_admission_number(self.cleaned_data.get('admission_number'))
        if not number:
            return None
        owner = Application.find_admission_number_owner(number, exclude_application_id=self.instance.pk)
        if owner:
            reference = getattr(owner, 'reference_number', None) or owner.admission_number
            raise forms.ValidationError(
                f'Admission number {number} is already used by {owner.full_name} ({reference}).',
                code='duplicate_admission_number',
            )
        return number

    def clean_date_of_birth(self):
        """Validate date of birth - student should be between 4 and 18 years old"""
        from datetime import date
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 4:
                raise forms.ValidationError('Student must be at least 4 years old.')
            if age > 18:
                raise forms.ValidationError('This program is for students under 18 years old.')
        return dob

    def save(self, commit=True):
        """Override save to set application type"""
        application = super().save(commit=False)
        application.application_type = 'ONLINE'
        if commit:
            application.save()
        return application
