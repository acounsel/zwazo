from django import forms
from django.forms import ModelForm, modelformset_factory

from .models import Prompt, Survey

class SurveyForm(ModelForm):

    class Meta(object):
        model = Survey
        fields = ('text_prompt', 'yes_no_prompt', 'numeric_prompt')
        widgets = {
            'text_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'text'}), 
            'yes_no_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'yes_no'}),
            'numeric_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'numeric'})
        }

    def __init__(self, *args, **kwargs):
        super(SurveyForm, self).__init__(*args, **kwargs)
        for field in Prompt.CATEGORY_CHOICES:
            print(field[0])
            self.fields['{}_prompt'.format(field[0])].queryset = Prompt.objects.filter(category=field[0])

class PromptForm(ModelForm):

    class Meta(object):
        model = Prompt
        fields = ('name', 'category', 'sound_file')

PromptFormSet = modelformset_factory(Prompt, fields=('name', 'category', 'sound_file'), extra=3)