from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path('user', views.UserRegisterView.as_view(), name='register'),
    path('user/login', views.UserLogin.as_view(), name='login'),
    path('user/logout', views.UserLogout.as_view(), name='logout'),
    path('user/rank', views.UserRankView.as_view(), name='user_rank'),
    path('admin/user', views.UserAdminView.as_view(), name='user_admin'),
    path('factory', views.FactoryMultiHandle.as_view(), name='factory'),
    path('app', views.AppMultiHandle.as_view(), name='app'),
    path('finger', views.FingerMultiHandle.as_view(), name='finger_multi'),
    path('finger/single', views.FingerSingleHandle.as_view(), name='finger_single'),
    path('admin/finger/supersubmit', views.FingerSuperSubmitHandle.as_view(), name='finger_supersubmit'),
    path('finger/single/check', views.FingerCheckHandle.as_view(), name='finger_single_check'),
    path('finger/single/query', views.FingerSingleQuery.as_view(), name='finger_single_query'),
    path('finger/batch/query', views.FingerBatchQuery.as_view(), name='finger_batch_query'),
    path('finger/batch/action', views.FingerBatchAction.as_view(), name='finger_batch_action'),
    path('admin/finger', views.FingerMultiAdminHandle.as_view(), name='finger_multi_admin'),
    path('admin/finger/single', views.FingerSingleAdminHandle.as_view(), name='finger_single_admin'),
    path('admin/finger/modify', views.FingerModifyAdminHandle.as_view(), name='finger_modify_admin'),
    path('admin/config', views.ConfigView.as_view(), name='config_admin'),
]