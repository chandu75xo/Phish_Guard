import uuid
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class URLPrediction(models.Model):
    RESULT_CHOICES = [
        ('Phishing',     'Phishing'),
        ('Non Phishing', 'Non Phishing'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    url        = models.TextField()
    result     = models.CharField(max_length=20, choices=RESULT_CHOICES)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']

    def __str__(self):
        return f"{self.url[:60]} → {self.result}"

    @property
    def is_phishing(self):
        return self.result == 'Phishing'


class ModelAccuracy(models.Model):
    model_name = models.CharField(max_length=100)
    accuracy   = models.FloatField()
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accuracy']

    def __str__(self):
        return f"{self.model_name}: {self.accuracy}%"


class PredictionJob(models.Model):
    """
    Background prediction job — lets users navigate away while analysis runs.
    The worker thread updates this record; the frontend polls /predict/status/<id>/
    """
    STATUS_PENDING  = 'pending'
    STATUS_RUNNING  = 'running'
    STATUS_DONE     = 'done'
    STATUS_ERROR    = 'error'
    STATUS_CHOICES  = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_DONE,    'Done'),
        (STATUS_ERROR,   'Error'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    url        = models.TextField()
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    result     = models.CharField(max_length=20, blank=True)
    accuracies = models.JSONField(default=dict)
    error_msg  = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Job {self.id} [{self.status}]"

    @property
    def is_phishing(self):
        return self.result == 'Phishing'
