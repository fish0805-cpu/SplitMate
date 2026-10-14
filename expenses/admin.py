from django.contrib import admin

from .models import Expense, Member, Trip


admin.site.register(Trip)
admin.site.register(Member)
admin.site.register(Expense)

