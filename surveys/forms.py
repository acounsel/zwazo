from django import forms
from django.forms import ModelForm, modelformset_factory

from .models import Prompt, Survey

class SurveyForm(ModelForm):

    class Meta(object):
        model = Survey
        fields = ('welcome_prompt', 'text_prompt', 'yes_no_prompt', 'numeric_prompt', 'goodbye_prompt')
        widgets = {
            'welcome_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'welcome'}), 
            'text_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'text'}), 
            'yes_no_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'yes_no'}),
            'numeric_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'numeric'}),
            'goodbye_prompt': forms.Select(attrs={'class': 'SelectizeCreate', 'category':'goodbye'}),
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


PromptFormSet = modelformset_factory(Prompt, 
                                    fields=('category', 'name', 'language', 'sound_file'), 
                                    widgets = {'category': forms.Select(attrs={'class': 'Selectize-Off FormField-NoBorder'}), 'language': forms.HiddenInput()},
                                    extra=5)
