# Create your views here.
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from ouser.forms import RegistrationForm, LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from ouser.models import Ouser


def OuserRegistration(request):
        if request.user.is_authenticated():
                return HttpResponseRedirect('/loggedin/')
        if request.method == 'POST':
                form = RegistrationForm(request.POST)
                if form.is_valid():
                        user = User.objects.create_user(username=form.cleaned_data['username'], email = form.cleaned_data['email'], password = form.cleaned_data['password'])
                        user.save()
                        ouser = Ouser(user=user, name=form.cleaned_data['name'])
                        ouser.save()
                        return HttpResponseRedirect('/loggedin/')
                else:
                        return render_to_response('register.html', {'form': form}, context_instance=RequestContext(request))
        else:
                ''' user is not submitting the form, show them a blank registration form '''
                form = RegistrationForm()
                context = {'form': form}
                return render_to_response('register.html', context, context_instance=RequestContext(request))
def LoginRequest(request):
        if request.user.is_authenticated():
                return HttpResponseRedirect('/loggedin/')
        if request.method == 'POST':
                form = LoginForm(request.POST)
                if form.is_valid():
                        username = form.cleaned_data['username']
                        password = form.cleaned_data['password']
                        ouser = authenticate(username=username, password=password)
                        if ouser is not None:
                                login(request, ouser)
                                return HttpResponseRedirect('/loggedin/')
                        else:
                                return render_to_response('login.html', {'form': form}, context_instance=RequestContext(request))
                else:
                        return render_to_response('login.html', {'form': form}, context_instance=RequestContext(request))
        else:
                ''' user is not submitting the form, show the login form '''
                form = LoginForm()
                context = {'form': form}
                return render_to_response('login.html', context, context_instance=RequestContext(request))

def LogoutRequest(request):
        logout(request)
        return HttpResponseRedirect('/')
