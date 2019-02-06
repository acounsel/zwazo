import csv

from django.db import models
from django.db.models import Count
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify

from accounts.models import Organization

def create_unique_slug(instance):
    iterator = 1
    slug = slugify(instance.name)
    while instance.__class__.objects.exclude(id=instance.id).filter(slug=slug):
        iterator += 1
        slug = slugify(instance.name) + str(iterator)
    return slug

class Language(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class CountryManager(models.Manager):

    def import_countries(self):
        with open('data/countries.csv', encoding="utf-8", errors='ignore') as csvfile:
            reader = csv.DictReader(csvfile)
            iterator = 0
            for row in reader:
                self.create(name=row['Name'], code=row['Code'])
                iterator += 1
        return iterator

class Country(models.Model):
    objects = CountryManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    code = models.CharField(max_length=5, blank=True)
    latitude = models.IntegerField(blank=True, null=True)
    longitude = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta(object):
        verbose_name_plural = 'countries'

    def save(self, *args, **kwargs):
        self.slug = create_unique_slug(self)
        super(Country, self).save(*args, **kwargs)

    def get_project_url(self, *args, **kwargs):
        return reverse('project-create')

class Project(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = create_unique_slug(self)
        super(Project, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'slug': self.slug})

class Contact(models.Model):
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=255, blank=True)
    has_consented = models.BooleanField(default=False)

    def __str__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)

    def get_absolute_url(self): 
        return reverse('contact-list') + '?project={0}'.format(getattr(self.project, 'id', ''))

class Survey(models.Model):
    name = models.CharField(max_length=255)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    respondents = models.ManyToManyField(Contact, blank=True)

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

class Question(models.Model):
    TEXT = 'text'
    YES_NO = 'yes-no'
    NUMERIC = 'numeric'

    QUESTION_KIND_CHOICES = (
        (TEXT, 'Text'),
        (YES_NO, 'Yes or no'),
        (NUMERIC, 'Numeric')
    )

    body = models.CharField(max_length=255)
    kind = models.CharField(max_length=255, choices=QUESTION_KIND_CHOICES, default=YES_NO)
    sound = models.CharField(max_length=255, blank=True)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)

    @classmethod
    def validate_kind(cls, kind):
        if kind not in [cls.YES_NO, cls.NUMERIC, cls.TEXT]:
            raise ValidationError("Invalid question type")

    def next(self):
        survey = Survey.objects.get(id=self.survey_id)

        next_questions = \
            survey.question_set.order_by('id').filter(id__gt=self.id)

        return next_questions[0] if next_questions else None

    def get_responses(self):
        return self.questionresponse_set.values('response').order_by('response').annotate(Count('response'))

    def __str__(self):
        return '%s' % self.body

class QuestionResponse(models.Model):
    response = models.CharField(max_length=255)
    call_sid = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255)
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

