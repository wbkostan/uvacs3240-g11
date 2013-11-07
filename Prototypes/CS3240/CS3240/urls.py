from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.views.generic import TemplateView


# Uncomment the next two lines to enable the admin:
from django.contrib import admin, auth
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'CS3240.views.home', name='home'),
    # url(r'^CS3240/', include('CS3240.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    #Login Views
#    url(r'^admin/password_change/$', 'OneDir.views.password_change()'),
    (r'^users/$', 'OneDir.views.UserAll'),
    (r'^$', TemplateView.as_view(template_name='index.html')),
    (r'^register/$', 'ouser.views.OuserRegistration'),
    (r'^login/$', 'ouser.views.LoginRequest'),
    (r'^loggedin/$', TemplateView.as_view(template_name='loggedin.html')),
    (r'^logout/$', 'ouser.views.LogoutRequest'),

) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
