# Create your views here.
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib import auth
from django.core.context_processors import csrf
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from OneDir.models import User

def UserAll(request):
    users = User.objects.all().order_by('name')
    context = {'users': users}
    return render_to_response('usersall.html', context, context_instance = RequestContext(request))



#def password_change(request):
#    return render_to_response('registration/password_change_form.html')



