
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _


class Activity(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": _("請輸入活動名稱。")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Member(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="members",
    )
    name = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "activity",
                name="unique_member_name_per_activity_ci",
            )
        ]
        ordering = ["pk"]

    def clean(self):
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": _("請輸入成員名稱。")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Expense(models.Model):
    class SplitMethod(models.TextChoices):
        EQUAL = "equal", _("平均分攤")
        CUSTOM = "custom", _("自訂金額")

    activity = models.ForeignKey(
        Activity,
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
    split_method = models.CharField(
        max_length=6,
        choices=SplitMethod.choices,
        default=SplitMethod.EQUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def clean(self):
        super().clean()
        self.title = self.title.strip()
        errors = {}
        if not self.title:
            errors["title"] = _("請輸入支出名稱。")
        if self.activity_id and self.paid_by_id:
            if self.paid_by.activity_id != self.activity_id:
                errors["paid_by"] = _("付款者必須屬於這個活動。")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ExpenseShare(models.Model):
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "member"],
                name="unique_member_share_per_expense",
            )
        ]
