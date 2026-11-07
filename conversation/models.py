"""Persistent interview bookings collected through the chat API."""

import uuid

from django.db import models


class InterviewBooking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254)
    interview_date = models.DateField()
    interview_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["interview_date", "interview_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["interview_date", "interview_time"],
                name="unique_interview_slot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} on {self.interview_date} at {self.interview_time}"
