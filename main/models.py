from django.db import models


class Groups(models.Model):
        code = models.IntegerField(primary_key=True)
        eu_name = models.CharField(max_length=50, unique=True)
        name = models.CharField(max_length=100)

        class Meta:
            verbose_name = "Country group"
            verbose_name_plural = "Country groups"

        def __str__(self):
            return self.name


class Country(models.Model):
        id = models.IntegerField(primary_key=True)
        name = models.CharField(max_length=100, unique=True)
        groups = models.ManyToManyField(Groups, related_name="countries", blank=True)

        class Meta:
            ordering = ["name"]

        def __str__(self):
            return self.name


class VisaStatus(models.Model):
        code = models.CharField(max_length=50, unique=True)
        name = models.CharField(max_length=100)
        description = models.TextField(blank=True)

        def __str__(self):
            return self.name


class VisaRule(models.Model):
        passport_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="visa_rules_from")
        destination_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="visa_rules_to")
        status = models.ForeignKey(VisaStatus, on_delete=models.PROTECT, related_name="visa_rules")
        days_without_visa = models.PositiveSmallIntegerField(null=True, blank=True)
        comments = models.TextField(blank=True)
        updated_at = models.DateTimeField(auto_now=True)

        class Meta:
            unique_together = ("passport_country", "destination_country")