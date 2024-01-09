from django import forms
from django.contrib.auth.forms import UserCreationForm


from .models import Matching, Availability


class MatchingForm(forms.ModelForm):
    class Meta:
        model = Matching
        fields = ['Fields', 'Degree', 'Skills', 'Objectives', 'Job', 'PersonalityDescription']

from .models import Mentor  # Assurez-vous d'importer le modèle Mentor

class MentorForm(forms.ModelForm):
    class Meta:
        model = Mentor
        fields = ['Fields', 'Degree', 'Skills', 'Objectives', 'Job', 'PersonalityDescription']

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']
