from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify


class Plan(models.Model):
    PER_USE = 'per_use'
    MONTHLY = 'monthly'
    ANNUAL = 'annual'
    PERIOD_CHOICES = (
        (PER_USE, 'Per Use'),
        (MONTHLY, 'Monthly'),
        (ANNUAL, 'Annual'),
    )
    name = models.CharField(max_length=255)
    period = models.CharField(max_length=50, choices=PERIOD_CHOICES, default=PER_USE)
    cost_per_use = models.IntegerField(default=100)
    cost_per_period = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Organization(models.Model):
    name = models.CharField(max_length=255)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.name

class Userprofile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    has_approved_terms = models.BooleanField(default=False)

    class Meta(object):
        ordering = ('user__first_name',)

    def __str__(self):
        return self.user.get_full_name()

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)