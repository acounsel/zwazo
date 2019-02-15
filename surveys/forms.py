from django import forms
from django.forms import ModelForm

from .models import Prompt, Survey

class SurveyForm(ModelForm):

    class Meta(object):
        model = Survey
        fields = ('name', 'language', 'text_prompt', 'yes_no_prompt', 'numeric_prompt')

    def __init__(self, *args, **kwargs):
        super(SurveyForm, self).__init__(*args, **kwargs)
        for field in Prompt.CATEGORY_CHOICES:
            print(field[0])
            self.fields['{}_prompt'.format(field[0])].queryset = Prompt.objects.filter(category=field[0])