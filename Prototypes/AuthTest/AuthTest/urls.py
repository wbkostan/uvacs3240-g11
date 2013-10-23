from django.conf.urls import patterns, include, url
from testing.views import hello, login_view

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'AuthTest.views.home', name='home'),
    # url(r'^AuthTest/', include('AuthTest.foo.urls')),
    url(r'^hello/',hello),
    url(r'^login/',login_view),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
