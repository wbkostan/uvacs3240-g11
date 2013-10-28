from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'Authentication.views.home', name='home'),
    # url(r'^Authentication/', include('Authentication.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    #user auth urls
    url(r'accounts/login/$', 'userauth.views.login'),
    url(r'accounts/auth/$', 'userauth.views.auth_view'),
    url(r'accounts/logout/$', 'userauth.views.logout'),
    url(r'accounts/loggedin/$', 'userauth.views.loggedin'),
    url(r'accounts/invalid/$', 'userauth.views.invalid_login'),
    url(r'accounts/register/$', 'userauth.views.register_user'),
    url(r'accounts/register_success/$', 'userauth.views.register_success'),
)
