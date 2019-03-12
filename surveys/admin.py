from django.contrib import admin

from surveys.models import Language, Country, Project, Contact, Prompt
from surveys.models import Survey, Question, QuestionResponse

admin.site.register(Language)
admin.site.register(Country)
admin.site.register(Project)
admin.site.register(Contact)
admin.site.register(Survey)

@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = (
        'question',
        'response',
        'contact',
    )
    list_display_links = (
        'question',
        'response',
        'contact',
    )
    list_select_related = ('question','contact')
    list_filter = ('question', 'question__kind', 'contact','question__survey')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'body',
        'kind',
        'survey',
    )
    list_display_links = (
        'body',
        'kind',
        'survey',
    )
    list_select_related = ('survey',)
    list_filter = ('kind','survey','survey__project')

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'language',
        'sound_file',
    )
    list_display_links = (
        'name',
        'category',
        'language',
    )
    list_select_related = ('language',)
    list_filter = ('category','language','is_default')