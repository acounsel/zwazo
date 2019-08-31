from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('incoming/', views.voice_response, name='incoming'),
    path('surveys/', include('surveys.urls')),
    path('broadcasts/', include('broadcasts.urls')),
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
            path('create/', views.CommunicationCreate.as_view(), name='communication-create'),
            path('contacts/', include([
                path('', views.ContactAdd.as_view(), name='contact-add'),
                path('import/', views.ContactImport.as_view(), name='contact-import'),
            ])),
        ])),
    ])),
]