__author__ = 'jha5cn'

from django.http import HttpResponse

def index(request):
    return HttpResponse("Arrived at index")

