from django.db import models
from surveys.models import Organization
from django.utils.text import slugify
from django.urls import reverse


def create_unique_slug(instance):
    iterator = 1
    slug = slugify(instance.name)
    while instance.__class__.objects.exclude(id=instance.id).filter(slug=slug):
        iterator += 1
        slug = slugify(instance.name) + str(iterator)
    return slug

class LanguageManager(models.Manager):
    def import_languages(self):
        with open('data/languages.csv', encoding="utf-8", errors='ignore') as csvfile:
            reader = csv.DictReader(csvfile)
            iterator = 0
            for row in reader:
                if row['Code']:
                    self.create(name=row['Name'], code=row['Code'])
                    iterator += 1
        return iterator

class Language(models.Model):
    objects = LanguageManager()

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=5, blank=True, null=True)

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
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, blank=True, null=True)
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
        return reverse('project-create') + '?country={}'.format(self.id)

class ProjectManager(models.Manager):
    
    def get_function_fields(self):
        return ('voice', 'sms', 'email', 'whatsapp')

class Project(models.Model):
    objects = ProjectManager()

    OFF = 'off'
    ONEWAY = 'oneway'
    TWOWAY = 'twoway'
    FEATURE_CHOICES = (
        (OFF, 'None'),
        (ONEWAY, 'One-Way'),
        (TWOWAY, 'Two-Way'),
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, blank=True, null=True)
    description = models.TextField(blank=True)
    voice = models.CharField(max_length=20, choices=FEATURE_CHOICES, default=OFF)
    sms = models.CharField(max_length=20, choices=FEATURE_CHOICES, default=OFF)
    email = models.CharField(max_length=20, choices=FEATURE_CHOICES, default=OFF)
    whatsapp = models.CharField(max_length=20, choices=FEATURE_CHOICES, default=OFF)

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
    project = models.ManyToManyField(Project, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.CharField(max_length=255, blank=True)
    has_consented = models.BooleanField(default=False)

    # class Meta(object):
    #     unique_together = (('project', 'phone'),)

    def __str__(self):
        return '{0} {1}'.format(self.first_name, self.last_name)

    def get_absolute_url(self): 
        return reverse('contact-list') + '?project={0}'.format(getattr(self.project, 'id', ''))
