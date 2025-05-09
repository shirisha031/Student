from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.custom_login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.custom_login_view, name='login'),  # Redirect root path to login
     path('student-data/', views.student_data_view, name='student_data_view'),

      path('messages/', views.compose_message, name='compose_message'),
       path('message-history/', views.message_history_view, name='message_history_view'),
]
