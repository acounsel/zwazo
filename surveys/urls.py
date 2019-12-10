from django.views.generic import TemplateView
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('surveys/', include([
        path('', views.SurveyList.as_view(), name='survey-list'),
        path('add/', views.SurveyCreate.as_view(), name='survey-create'),
        path('<int:pk>/', include([
            path('', views.SurveyDetail.as_view(), name='survey-detail'),
            path('run/', views.run_survey, name='run-survey'),
            path('update/', views.SurveyUpdate.as_view(), name='survey-update'),
            path('responses/', views.SurveyResponse.as_view(), name='survey-response'),
            path('export/', views.SurveyExport.as_view(), name='survey-export'),
            path('prompts/', include([
                path('', views.SurveyPrompts.as_view(), name='survey-prompts'),
                path('sound/', views.SurveyPromptSound.as_view(), name='survey-prompt-sound'),
            ])),
            path('questions/', include([
                path('', views.QuestionList.as_view(), name='question-list'),
                path('add/', views.QuestionCreate.as_view(), name='question-create'),
                path('actions/', views.ResponseActionCreate.as_view(), name='response-action-create'),
                path('<int:question_pk>/', include([
                    path('', views.QuestionDetail.as_view(), name='question-detail'),
                    path('run/', views.run_question, name='run-question'),
                    path('save/', views.save_response, name='save_response'),
                    path('next/', views.run_question, name='question'),
                    path('update/', views.QuestionUpdate.as_view(), name='question-update'),
                    path('sound/', views.QuestionSound.as_view(), name='question-sound'),
                    path('remove/', views.QuestionDelete.as_view(), name='question-delete'),
                ])),
            ])),
        ])),
    ])),
    path('prompts/', include([
        path('', views.PromptView.as_view(), name='prompt-list'),
        path('add/', views.PromptCreate.as_view(), name='prompt-create'),
        path('<int:pk>/', include([
            path('', views.PromptDetail.as_view(), name='prompt-detail'),
            path('update/', views.PromptUpdate.as_view(), name='prompt-detail'),
        ])),
    ])),
    path('contacts/', include([
        path('', views.ContactList.as_view(), name='contact-list'),
        path('add/', views.ContactCreate.as_view(), name='contact-create'),
        path('<int:pk>/', include([
            path('', views.ContactDetail.as_view(), name='contact-detail'),
            path('update/', views.ContactUpdate.as_view(), name='contact-update'),
            path('remove/', views.ContactRemove.as_view(), name='contact-remove'),
        ])),
    ])),
    path('projects/', include([
        path('', views.ProjectList.as_view(), name='project-list'),
        path('add/', views.ProjectCreate.as_view(), name='project-create'),
        path('<slug>/', include([
            path('', views.ProjectDetail.as_view(), name='project-detail'),
            path('update/', views.ProjectUpdate.as_view(), name='project-update'),
            path('contacts/', include([
                path('', views.ContactAdd.as_view(), name='contact-add'),
                path('import/', views.ContactImport.as_view(), name='contact-import'),
            ])),
        ])),
    ])),
]