from django import forms

from workgroup.models import WorkGroup


class RevisionForm(forms.ModelForm):
    class Meta:
        model = WorkGroup
        fields = ['name', 'description', 'avatar']