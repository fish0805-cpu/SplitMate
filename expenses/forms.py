from django import forms
from django.forms import BaseFormSet, formset_factory

from .models import Expense, Member, Trip


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["name"]
        labels = {"name": "旅程名稱"}
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "例如：Tokyo Trip", "autocomplete": "off"}
            )
        }


class MemberForm(forms.Form):
    name = forms.CharField(
        max_length=80,
        label="成員名稱",
        widget=forms.TextInput(
            attrs={"placeholder": "輸入成員名稱", "autocomplete": "off"}
        ),
    )


class BaseMemberFormSet(BaseFormSet):
    default_error_messages = {
        **BaseFormSet.default_error_messages,
        "too_few_forms": "至少需要 2 位成員。",
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
            raise forms.ValidationError("成員名稱不可重複。")


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
        fields = ["title", "amount", "paid_by", "participants"]
        labels = {
            "title": "支出名稱",
            "amount": "金額",
            "paid_by": "付款者",
            "participants": "參與分攤成員",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "例如：晚餐", "autocomplete": "off"}
            ),
            "amount": forms.NumberInput(
                attrs={"placeholder": "0", "min": "0.01", "step": "0.01"}
            ),
            "participants": forms.CheckboxSelectMultiple(),
        }
        error_messages = {
            "participants": {"required": "至少選擇一位參與成員。"},
        }

    def __init__(self, *args, trip: Trip, **kwargs):
        super().__init__(*args, **kwargs)
        members = Member.objects.filter(trip=trip).order_by("pk")
        self.fields["paid_by"].queryset = members
        self.fields["participants"].queryset = members

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("金額必須大於 0。")
        return amount

