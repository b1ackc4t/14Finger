from django.contrib.auth.backends import ModelBackend
from .models import User

class UserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username:
            user = User.objects.get(username=username)
        else:
            user = User.objects.get(email=kwargs['email'])
        if user.check_password(password):
            return user
        else:
            return None



