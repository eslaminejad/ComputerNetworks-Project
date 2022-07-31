from django.urls import path

from .views import *

app_name = 'users'

urlpatterns = [
    path("register/", RegisterFormView.as_view(), name="register"),
    path('login/', LoginFormView.as_view(), name='login'),
    path('logout/', logout_user, name='logout'),
]
