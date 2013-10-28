__author__ = 'jha5cn'

from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^HTTP/', include ('HTTP.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
