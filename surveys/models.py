import csv

from django.db import models
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.urls import reverse

from zwazo.storage_backends import PrivateMediaStorage

from accounts.models import Organization
from base_site.models import Language, LanguageManager, CountryManager, Country, ProjectManager, Project, Contact

class Prompt(models.Model):
    NUMERIC = 'numeric'
    TEXT = 'text'
    YES_NO = 'yes_no'
    WELCOME = 'welcome'
    GOODBYE = 'goodbye'
    CATEGORY_CHOICES = (
        (NUMERIC, 'Numeric'),
        (TEXT, 'Text'),
        (YES_NO, 'Yes/No'),
        (WELCOME, 'Welcome'),
        (GOODBYE, 'Goodbye'),
    )

    name = models.CharField(max_length=255)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    sound_file = models.FileField(storage=PrivateMediaStorage(), upload_to='files/', blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return '%s' % self.name

    def get_twiml_data(self, prompt_type):
        if prompt_type == Survey.SOUND:
            verb, args, kwargs = 'play', (self.sound_file.url,), {}
        else:
            verb = 'say'
            args = (self.name,)
            kwargs = {
                'voice': 'alice',
                'language': self.language.code,
            }
        return verb, args, kwargs
        
class Survey(models.Model):
    VOICE = 'voice'
    SMS = 'sms'
    WHATSAPP = 'whatsapp'
    SURVEY_CHOICES = (
        (VOICE, 'Voice'),
        (SMS, 'SMS'),
        (WHATSAPP, 'WhatsApp'),
    )
    DEFAULT = 'default'
    TEXT = 'text'
    SOUND = 'sound'
    NONE = 'none'
    PROMPT_CHOICES = (
        (DEFAULT, 'Default Prompts'),
        (TEXT, 'Custom Text'),
        (SOUND, 'Custom Sound'),
        (NONE, 'No Prompts')
    )

    name = models.CharField(max_length=255)
    survey_type = models.CharField(max_length=30, choices=SURVEY_CHOICES, default=VOICE)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    prompt_type = models.CharField(max_length=50, choices=PROMPT_CHOICES, default=DEFAULT)
    welcome_prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, blank=True, null=True, related_name='welcome_surveys')
    text_prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, blank=True, null=True, related_name='text_surveys')
    yes_no_prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, blank=True, null=True, related_name='yes_no_surveys')
    numeric_prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, blank=True, null=True, related_name='numeric_surveys')
    goodbye_prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, blank=True, null=True, related_name='goodbye_surveys')
    respondents = models.ManyToManyField(Contact, blank=True)
    is_callback = models.BooleanField(default=False)

    @property
    def responses(self):
        return QuestionResponse.objects.filter(question__survey__id=self.id)

    @property
    def first_question(self):
        return Question.objects.filter(survey__id=self.id
                                       ).order_by('id').first()
    def __str__(self):
        return '%s' % self.name

    def get_absolute_url(self):
        return reverse('survey-detail', kwargs={'pk':self.id})

    def get_prompt_url(self):
        if self.prompt_type == self.TEXT:
            return reverse('survey-prompts', kwargs={'pk':self.id})
        elif self.prompt_type == self.SOUND:
            return reverse('survey-prompt-sound', kwargs={'pk':self.id}) 
        else:
            self.add_prompts(prompts=Prompt.objects.filter(is_default=True))
            return reverse('question-create', kwargs={'pk':self.id})  

    def add_prompts(self, prompts):
        for prompt in prompts:
            setattr(self, '{}_prompt'.format(prompt.category), prompt)
        self.save()
        return self

    def get_prompt(self, kind):
        prompt = getattr(self, '{}_prompt'.format(kind))
        # prompt = getattr(self, '{}_prompt'.format(self.kind.replace('-','_')))
        return prompt.get_twiml_data(self.prompt_type)

    def say_prompt(self, twiml, kind):
        verb, args, kwargs = self.get_prompt(kind=kind)
        getattr(twiml, verb)(*args, **kwargs)
        return twiml

class Question(models.Model):
    TEXT = 'text'
    YES_NO = 'yes_no'
    NUMERIC = 'numeric'

    QUESTION_KIND_CHOICES = (
        (TEXT, 'Text'),
        (YES_NO, 'Yes or no'),
        (NUMERIC, 'Numeric'),
    )

    body = models.CharField(max_length=255)
    kind = models.CharField(max_length=255, choices=QUESTION_KIND_CHOICES, default=YES_NO)
    sound = models.CharField(max_length=255, blank=True)
    sound_file = models.FileField(storage=PrivateMediaStorage(), upload_to='files/', blank=True, null=True)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    # message = models.ForeignKey(Message, on_delete=models.CASCADE)
    repeater = models.CharField(max_length=2, blank=True)
    terminator = models.CharField(max_length=2, blank=True)
    max_length = models.IntegerField(default=1)
    timeout = models.IntegerField(default=5)
    has_prompt = models.BooleanField(default=True)

    @classmethod
    def validate_kind(cls, kind):
        if kind not in [cls.YES_NO, cls.NUMERIC, cls.TEXT]:
            raise ValidationError("Invalid question type")

    def next(self, response=None):
        if response:
            if response.is_repeater():
                return self
            elif response.is_terminator():
                return None
        next_questions = self.get_next_questions()

        return next_questions[0] if next_questions else None

    def get_next_questions(self):
        survey = Survey.objects.get(id=self.survey_id)
        next_questions = \
            survey.question_set.order_by('id').filter(id__gt=self.id)
        return next_questions

    def get_responses(self):
        return self.questionresponse_set.values('response').order_by('response').annotate(Count('response'))

    def __str__(self):
        return '%s' % self.body

    def get_twiml_data(self):
        if self.sound_file:
            verb, args, kwargs = 'play', (self.sound_file.url,), {}
        else:
            verb = 'say'
            args = (self.body,)
            kwargs = {
                'voice': 'alice',
                'language': self.survey.language.code,
            }
        return verb, args, kwargs

    def say_question(self, twiml):
        verb, args, kwargs = self.get_twiml_data()
        getattr(twiml, verb)(*args, **kwargs)
        return twiml

    def say_question_and_prompt(self, twiml):
        twiml = self.say_question(twiml)
        if self.has_prompt:
            twiml = self.survey.say_prompt(twiml, self.kind)
        return twiml

class QuestionResponse(models.Model):
    response = models.CharField(max_length=255)
    transcription = models.TextField(blank=True)
    call_sid = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    def __str__(self):
        return '%s' % self.response

    def as_dict(self):
        return {
                'body': self.question.body,
                'kind': self.question.kind,
                'response': self.response,
                'call_sid': self.call_sid,
                'phone_number': self.phone_number,
                }

    def is_repeater(self):
        if self.question.repeater:
            if self.response == self.question.repeater:
                return True
        return False

    def is_terminator(self):
        if self.question.terminator:
            if self.response == self.question.terminator:
                return True
        return False

