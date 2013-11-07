from django.db import models

USER_TYPE = (
    ('U', 'USER'),
    ('A', 'ADMIN')
)

# Create your models here.
class User(models.Model):
    name = models.CharField(max_length=200, unique = True)
    password = models.CharField(max_length = 200)
    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=1, choices=USER_TYPE)
    directory = models.ForeignKey("Directory")

    def __unicode__(self):
        return self.name

class Directory(models.Model):
    dirname = models.SlugField(max_length=200, unique = True)
    slug = models.SlugField(unique =True)

    def __unicode__(self):
        return self.dirname