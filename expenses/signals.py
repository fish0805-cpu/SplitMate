
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Expense


@receiver(m2m_changed, sender=Expense.participants.through)
def validate_participant_trip(sender, instance, action, reverse, pk_set, **kwargs):
    if action != "pre_add" or not pk_set:
        return

    if reverse:
        has_outsider = Expense.objects.filter(pk__in=pk_set).exclude(
            trip_id=instance.trip_id
        ).exists()
    else:
        has_outsider = instance.participants.model.objects.filter(
            pk__in=pk_set
        ).exclude(trip_id=instance.trip_id).exists()

    if has_outsider:
        raise ValidationError("參與分攤的成員必須屬於這個旅程。")
