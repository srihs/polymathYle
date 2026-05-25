from django import forms
from .models import Application


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
