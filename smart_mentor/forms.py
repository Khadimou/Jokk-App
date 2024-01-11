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


from django.utils.translation import gettext_lazy as _

class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['avatar', 'birthdate', 'gender', 'country', 'skills', 'phone', 'bio', 'social_media_links']
        labels = {
            'avatar': _('Avatar'),
            'birthdate': _('Birthdate'),
            'gender': _('Gender'),
            'country': _('Country'),
            'skills': _('Skills'),
            'phone': _('Phone'),
            'bio': _('Biography'),
            'social_media_links': _('Social Media Links'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_language = get_language() or settings.LANGUAGE_CODE
        date_format = settings.DATE_FORMATS.get(current_language, '%Y-%m-%d')

        self.fields['birthdate'].widget = forms.DateInput(
            format=date_format,
            attrs={'placeholder': _('MM/DD/YYYY') if current_language == 'en' else _('JJ/MM/AAAA')}
        )
        self.fields['birthdate'].input_formats = [date_format]

        # Ajout de la traduction pour les champs si nécessaire
        # for field_name in self.fields:
        #     field = self.fields[field_name]
        #     field.widget.attrs['placeholder'] = _(field.label)
