from django import forms
from django.forms import ModelForm, inlineformset_factory

from .models import Prompt, Survey

class SurveyForm(ModelForm):

    class Meta(object):
        model = Survey
        fields = ('name', 'language', 'text_prompt', 'yes_no_prompt', 'numeric_prompt')
        widgets = {
            'text_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'data-data': Prompt.TEXT}), 
            'yes_no_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'data-data': Prompt.YES_NO}), 
            'numeric_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'data-data': Prompt.NUMERIC})
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

# PromptFormSet = inlineformset_factory(Prompt, Survey, form=PromptForm, extra=3)