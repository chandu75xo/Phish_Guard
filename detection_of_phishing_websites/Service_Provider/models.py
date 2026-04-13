from django.db import models


class AdminSession(models.Model):
    """Tracks admin login sessions — lightweight, no Django User needed."""
    login_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admin session at {self.login_at}"
