
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
    class Category(models.TextChoices):
        FOOD = "food", _("餐飲")
        LODGING = "lodging", _("住宿")
        TRANSPORTATION = "transportation", _("交通")
        ACTIVITY = "activity", _("活動")
        SHOPPING = "shopping", _("購物")
        OTHER = "other", _("其他")

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
    category = models.CharField(
        max_length=14,
        choices=Category.choices,
        default=Category.OTHER,
        blank=True,
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
        self.category = self.category or self.Category.OTHER
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


class SettlementPayment(models.Model):
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="settlement_payments",
    )
    debtor = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="settlement_payments_to_make",
    )
    creditor = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="settlement_payments_to_receive",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "debtor", "creditor"],
                name="unique_settlement_payment_per_pair",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.debtor_id and self.debtor.activity_id != self.activity_id:
            errors["debtor"] = _("付款人必須屬於這個活動。")
        if self.creditor_id and self.creditor.activity_id != self.activity_id:
            errors["creditor"] = _("收款人必須屬於這個活動。")
        if self.debtor_id and self.debtor_id == self.creditor_id:
            errors["creditor"] = _("付款人與收款人不可相同。")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
