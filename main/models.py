from django.db import models

from django.db.models import SET_NULL, CASCADE, JSONField, IntegerField, DateField, DateTimeField, \
    FloatField, CharField, TextField, Model, BooleanField, ForeignKey


class Person(Model):
    # todo: Put this in.
    # user = models.OneToOneField(
    #     User, null=True, blank=True, related_name="person", on_delete=SET_NULL
    # )
    pass

    def __str__(self):
        return f""

    class Meta:
        # ordering = ["-datetime"]
        pass


class Institution(Model):
    name = CharField(max_length=50)


class Account(Model):
    person = ForeignKey(Person, on_delete=CASCADE)
    institution = ForeignKey(Institution, on_delete=CASCADE)
    name = CharField(max_length=50)


class Transaction(Model):
    account = ForeignKey(Account, on_delete=CASCADE)
    amount = FloatField()
    description = TextField()
    dt = DateTimeField()





