from django.conf.urls import patterns, url
from Prototypes.HTTP import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index')
)