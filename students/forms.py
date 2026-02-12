from django import forms
from .models import Application


class ApplicationForm(forms.ModelForm):
    """
    Online application form for Cambridge English Young Learners program
    """

    class Meta:
        model = Application
        fields = [
            'name_with_initials', 'full_name', 'date_of_birth', 'gender', 'nationality',
            'student_email', 'current_school', 'siblings_info',
            'mother_name', 'mother_contact_number', 'mother_occupation',
            'father_name', 'father_contact_number', 'father_occupation',
            'home_address', 'whatsapp_number', 'primary_contact_email',
            'special_comments', 'terms_accepted'
        ]

        widgets = {
            'name_with_initials': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Y.M. Minuli Sanindi Liyansha Yapa'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minuli Sanindi Liyansha Yapa'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'nationality': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sinhalese'
            }),
            'student_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@email.com'
            }),
            'current_school': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Polymath College'
            }),
            'siblings_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Names and levels of siblings currently attending (if any)'
            }),

            # Mother's Information
            'mother_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'K.G. Pradeepa Udayangani Jayalath'
            }),
            'mother_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0771234567'
            }),
            'mother_occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teacher'
            }),

            # Father's Information
            'father_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Y.M. Jagath Manjula Yapa'
            }),
            'father_contact_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0771234567'
            }),
            'father_occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business'
            }),

            # Contact Information
            'home_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'No. 20, 2nd Lane, Gammana Rd, Maharagama'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0771234567'
            }),
            'primary_contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'parent@email.com'
            }),

            # Special Comments
            'special_comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any additional information you would like to share...'
            }),

            # Terms
            'terms_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_terms_accepted(self):
        """Ensure terms are accepted"""
        terms = self.cleaned_data.get('terms_accepted')
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
