from django.contrib import admin

from accounts.models import Plan, Organization, Userprofile

admin.site.register(Plan)
admin.site.register(Organization)
admin.site.register(Userprofile)