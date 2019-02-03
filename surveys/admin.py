from django.contrib import admin

from surveys.models import Language, Country, Project, Contact
from surveys.models import Survey, Question, QuestionResponse

admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Project)
admin.site.register(Contact)
admin.site.register(Survey)
admin.site.register(Question)

@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = (
        'question',
        'response',
    )
    list_display_links = (
        'question',
        'response',
    )
    list_select_related = ('question',)
    list_filter = ('question',)
