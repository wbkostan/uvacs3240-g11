# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import auth

def hello(request):
    html = "<html><body>Hello World!</body></html>"
    html2 = """<html>
    <form>
    Username: <input type="text" name="username"><br>
    New Password: <input type="password" name="pwd"><br>
    Re-Type Password: <input type="password" name="pwd"><br>
    <input type="submit" value="Submit">
    </form>
    </html>"""
    return HttpResponse(html2)

def login_view(request):
    username = request.POST.get('username', 'faye')
    password = request.POST.get('password', 'KIRBYnight123')
    user = auth.authenticate(username = username, password = password)
    if user is not None and user.is_active:
        auth.login(request, user)
        return HttpResponseRedirect("/admin/")
    else:
        return HttpResponseRedirect("/hello/")