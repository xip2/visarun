from django.db import models


class Groups(models.Model):
        code = models.IntegerField(primary_key=True)
        eu_name = models.CharField(max_length=50, unique=True)
        name = models.CharField(max_length=100)

        def __str__(self):
            return self.name

        class Meta:
            db_table = 'groups'
            managed = False

class Country(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    groups = models.ManyToManyField(Groups,through='CountryGroup',related_name='countries', blank=True,)

    class Meta:
        db_table = 'country'
        managed = False

    def __str__(self):
        return self.name

class CountryGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    country = models.ForeignKey(Country, db_column='country_id', on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Groups, db_column='groups_id', on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'country_groups'
        managed = False

class VisaType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'visa_type'
        managed = False


class CountryVisa(models.Model):
    country = models.ForeignKey(Country, db_column='country_id', on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=255)
    visa_type = models.ForeignKey(VisaType, db_column='visa_type', on_delete=models.DO_NOTHING)
    days_without_visa = models.IntegerField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'country_visa'
        managed = False

