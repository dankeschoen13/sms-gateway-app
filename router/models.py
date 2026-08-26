from django.db import models

class Message(models.Model):
    sender_number = models.CharField(max_length=20)
    message_body = models.TextField()
    department = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True) # default=timezone.now for easy manual override during testing
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        # This determines how the object is displayed in the Django Admin or console
        return f"{self.sender_number} [{self.department}] - Blocked: {self.is_blocked}"

    