from django import forms
from django.forms import ModelForm, modelformset_factory

from .models import Broadcast

# class BroadcastForm(ModelForm):

#     class Meta(object):
#         model = Broadcast

#     def __init__(self, *args, **kwargs):
#         super(BroadcastForm, self).__init__(*args, **kwargs)

# class PromptForm(ModelForm):

#     class Meta(object):
#         model = Prompt
#         fields = ('name', 'category', 'sound_file')


# PromptFormSet = modelformset_factory(Prompt, 
#                                     fields=('category', 'name', 'language', 'sound_file'), 
#                                     widgets = {'category': forms.Select(attrs={'class': 'Selectize-Off FormField-NoBorder'}), 'language': forms.HiddenInput()},
#                                     extra=5)
