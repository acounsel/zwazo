from django.views.generic import TemplateView
from django.urls import path, include

from . import views

app_name = 'broadcast'
urlpatterns = [
    path('', include([
        path('', views.BroadcastList.as_view(), name='broadcast-list'),
        path('add/', views.BroadcastCreate.as_view(), name='broadcast-create'),
        path('<int:pk>/', include([
            path('', views.BroadcastDetail.as_view(), name='broadcast-detail'),
            path('delete', views.BroadcastDelete.as_view(), name='broadcast-delete'),
            path('update/', views.BroadcastUpdate.as_view(), name='broadcast-update'),
            path('run/', views.run_broadcast, name='run-broadcast'),
            path('manage/', views.BroadcastContactUpdate.as_view(), name='manage-contacts'),         
        ])),
    ])),
]