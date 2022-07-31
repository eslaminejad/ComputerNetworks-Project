from django.shortcuts import render

# Create your views here.
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from django.contrib.auth import authenticate, login, logout
from users.forms import *
from users.models import *


def index(request):
    return render(request, 'base.html')


class RegisterFormView(FormView):
    template_name = 'users/register.html'
    form_class = RegisterForm
    success_url = 'index'

    def form_valid(self, form):
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        email = form.cleaned_data['email']
        phone_number = form.cleaned_data['phone_number']
        user_type = form.cleaned_data['user_type']
        users = User.objects.filter(username=username)

        if users:
            return render(self.request, self.template_name, {"error": True, "username_unavailable": True})
        else:
            user = User(username=username, first_name=first_name, last_name=last_name, email=email,
                        phone_number=phone_number, user_type=user_type)
            user.set_password(password)
            try:
                user.save()
            except IntegrityError:
                return render(self.request, self.template_name, {"error": True, "duplicate_phone_number": True})
            if user.user_type == '1':
                return redirect(reverse("login"))
            else:
                return redirect(reverse("add-shop"))


class LoginFormView(FormView):
    template_name = 'users/login.html'
    form_class = LoginForm
    success_url = 'get-carpet-cleanings'

    def get(self, request, *args, **kwargs):
        if self.request.GET.get('signed_up') == 'true':
            return self.render_to_response(self.get_context_data(message="ثبت نام با موفقیت انجام شد."))
        else:
            return self.render_to_response(self.get_context_data())

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            if user.user_type != UserType.customer:
                return render(self.request, "users/login.html", {"error": True, "user_type_error": True})
            else:
                login(self.request, user)
                return redirect("get-carpet-cleanings")
        else:
            return render(self.request, "users/login.html", {"error": True, "login_error": True})


def logout_user(request):
    logout(request)
    return redirect('index')
