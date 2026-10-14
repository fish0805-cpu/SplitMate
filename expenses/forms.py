from django import forms
from django.forms import BaseFormSet, formset_factory

from .models import Trip


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

