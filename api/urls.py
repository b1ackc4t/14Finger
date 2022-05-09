from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path('user', views.UserRegisterView.as_view(), name='register'),
    path('user/login', views.UserLogin.as_view(), name='login'),
    path('user/logout', views.UserLogout.as_view(), name='logout'),
]