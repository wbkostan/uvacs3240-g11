from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User

# Create your models here.

class Ouser(models.Model):
        user            = models.OneToOneField(User)
        name            = models.CharField(max_length=100)

        def __unicode__(self):
                return self.name
