from django.views.generic import TemplateView
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('surveys/', include([
        path('', views.SurveyList.as_view(), name='survey-list'),
        path('add/', views.SurveyCreate.as_view(), name='survey-create'),
        path('<int:pk>', include([
            path('', views.SurveyDetail.as_view(), name='survey-detail'),
            path('update/', views.ContactUpdate.as_view(), name='contact-update'),
        ])),
    ])),
    path('contacts/', include([
        path('', views.ContactList.as_view(), name='contact-list'),
        path('add/', views.ContactCreate.as_view(), name='contact-create'),
        path('<int:pk>', include([
            path('', views.ContactDetail.as_view(), name='contact-detail'),
            path('update/', views.ContactUpdate.as_view(), name='contact-update'),
        ])),
    ])),
    path('projects/', include([
        path('', views.ProjectList.as_view(), name='project-list'),
        path('add/', views.ProjectCreate.as_view(), name='project-create'),
        path('<slug>', include([
            path('', views.ProjectDetail.as_view(), name='project-detail'),
            path('update/', views.ProjectUpdate.as_view(), name='project-update'),
        ])),
    ])),
]