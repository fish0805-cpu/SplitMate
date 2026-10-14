from django.contrib import admin

from .models import Activity, Expense, Member


admin.site.register(Activity)
admin.site.register(Member)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    # Custom shares are created and validated by the public expense form.
    exclude = ("split_method",)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.split_method == Expense.SplitMethod.CUSTOM:
            return False
        return super().has_change_permission(request, obj)

