from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.utils.translation import get_language

from smart_mentor.models import Profile


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Login'))


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput())
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput())
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput())
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I accept the conditions and terms of use"
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'accept_terms')

class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['avatar', 'birthdate', 'gender', 'country', 'education_level', 'skills', 'phone', 'bio', 'social_media_links']

    def __init__(self, *args, **kwargs):
        birthdate = forms.DateField(
            widget=forms.DateInput(
                format=settings.DATE_FORMATS[get_language()],
                attrs={'placeholder': 'MM/DD/YYYY' if get_language() == 'en' else 'JJ/MM/AAAA'}
            ),
            input_formats=[settings.DATE_FORMATS[get_language()]],
        )
        super().__init__(*args, **kwargs)
        current_language = get_language() or settings.LANGUAGE_CODE  # Utilisez la langue par défaut si get_language() renvoie None
        date_format = settings.DATE_FORMATS.get(current_language, '%Y-%m-%d')  # Format de date par défaut

        self.fields['birthdate'].widget = forms.DateInput(format=date_format)