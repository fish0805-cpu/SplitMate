
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class Trip(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "請輸入旅程名稱。"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Member(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="members",
    )
    name = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "trip",
                name="unique_member_name_per_trip_ci",
            )
        ]
        ordering = ["pk"]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "請輸入成員名稱。"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Expense(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    title = models.CharField(max_length=160)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    paid_by = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="expenses_paid",
    )
    participants = models.ManyToManyField(
        Member,
        related_name="expenses_shared",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def clean(self):
        super().clean()
        self.title = self.title.strip()
        errors = {}
        if not self.title:
            errors["title"] = "請輸入支出名稱。"
        if self.trip_id and self.paid_by_id:
            if self.paid_by.trip_id != self.trip_id:
                errors["paid_by"] = "付款者必須屬於這個旅程。"
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title
