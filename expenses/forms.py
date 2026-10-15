from django import forms
from django.forms import BaseFormSet, formset_factory
from django.utils.translation import gettext_lazy as _

from .models import Activity, Expense, Member


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["name"]
        labels = {"name": _("活動名稱")}
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": _("例如：週五晚餐、東京旅行"), "autocomplete": "off"}
            )
        }


class MemberForm(forms.Form):
    name = forms.CharField(
        max_length=80,
        label=_("成員名稱"),
        widget=forms.TextInput(
            attrs={"placeholder": _("輸入成員名稱"), "autocomplete": "off"}
        ),
    )


class BaseMemberFormSet(BaseFormSet):
    default_error_messages = {
        **BaseFormSet.default_error_messages,
        "too_few_forms": _("至少需要 2 位成員。"),
    }

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        names = [
            form.cleaned_data["name"].strip()
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("name", "").strip()
        ]
        normalized_names = [name.casefold() for name in names]
        if len(normalized_names) != len(set(normalized_names)):
            raise forms.ValidationError(_("成員名稱不可重複。"))


MemberFormSet = formset_factory(
    MemberForm,
    formset=BaseMemberFormSet,
    extra=0,
    min_num=2,
    validate_min=True,
    can_delete=True,
)


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["title", "amount", "category", "paid_by", "participants", "split_method"]
        labels = {
            "title": _("支出名稱"),
            "amount": _("金額"),
            "category": _("分類"),
            "paid_by": _("付款者"),
            "participants": _("參與分攤成員"),
            "split_method": _("分攤方式"),
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": _("例如：晚餐"), "autocomplete": "off"}
            ),
            "amount": forms.NumberInput(
                attrs={"placeholder": "0", "min": "0.01", "step": "0.01"}
            ),
            "participants": forms.CheckboxSelectMultiple(),
            "split_method": forms.RadioSelect(),
        }
        error_messages = {
            "participants": {"required": _("至少選擇一位參與成員。")},
        }

    def __init__(self, *args, activity: Activity, **kwargs):
        super().__init__(*args, **kwargs)
        members = Member.objects.filter(activity=activity).order_by("pk")
        saved_shares = {}
        if not self.is_bound and self.instance.pk:
            saved_shares = dict(
                self.instance.shares.values_list("member_id", "amount")
            )
        self.fields["paid_by"].queryset = members
        self.fields["participants"].queryset = members
        self.share_rows = []
        for member in members:
            field_name = f"share_{member.pk}"
            self.fields[field_name] = forms.DecimalField(
                max_digits=12,
                decimal_places=2,
                min_value=0,
                required=False,
                label=member.name,
                initial=saved_shares.get(member.pk),
                widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0.00"}),
            )
            self.share_rows.append({"member": member, "field": self[field_name]})
        self.fields["split_method"].required = False
        if self.is_bound:
            selected = set(self.data.getlist("participants"))
            is_custom = self.data.get("split_method") == Expense.SplitMethod.CUSTOM
            self.data = self.data.copy()
            for row in self.share_rows:
                if not is_custom or str(row["member"].pk) not in selected:
                    self.data.pop(f"share_{row['member'].pk}", None)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError(_("金額必須大於 0。"))
        return amount

    def clean_split_method(self):
        return self.cleaned_data["split_method"] or Expense.SplitMethod.EQUAL

    def clean(self):
        cleaned_data = super().clean()
        self.custom_shares = {}
        if cleaned_data.get("split_method") != Expense.SplitMethod.CUSTOM:
            return cleaned_data

        participants = cleaned_data.get("participants")
        amount = cleaned_data.get("amount")
        if participants is None or amount is None:
            return cleaned_data

        for member in participants:
            field_name = f"share_{member.pk}"
            share = cleaned_data.get(field_name)
            if share is None and field_name not in self.errors:
                self.add_error(field_name, _("請填寫每位分攤成員的金額。"))
            elif share is not None and share <= 0:
                self.add_error(field_name, _("每位分攤成員的金額必須大於 0。"))
            elif share is not None:
                self.custom_shares[member.pk] = share

        if not self.errors and sum(self.custom_shares.values()) != amount:
            self.add_error(None, _("每人分攤金額加總必須等於支出金額。"))
        return cleaned_data

