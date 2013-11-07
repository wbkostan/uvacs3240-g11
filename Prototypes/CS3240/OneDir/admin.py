__author__ = 'Audrey'

from django.contrib import admin
from OneDir.models import User, Directory

class UserAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('name',)}
    list_display = ('name', 'directory',)
    search_fields = ['name']

class DirectoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug':('dirname',)}

admin.site.register(User, UserAdmin)
admin.site.register(Directory, DirectoryAdmin)
