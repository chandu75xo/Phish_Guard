import threading
import logging
from functools import wraps

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import UserProfile, URLPrediction, ModelAccuracy, PredictionJob
from .forms import RegisterForm

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# AJAX-aware auth decorator
# Returns JSON 401 when an AJAX request hits a protected view without a session.
# ─────────────────────────────────────────────────────────────────────────────

def ajax_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
                return JsonResponse(
                    {'error': 'session_expired',
                     'redirect': f'/login/?next={request.path}'},
                    status=401
                )
            return redirect(f'/login/?next={request.path}')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────────────────────────────────────

def _run_prediction_job(job_id):
    """
    Runs in a daemon thread. Loads cached models, predicts, saves result.
    Uses Django ORM — must be called after Django setup.
    """
    import django
    from django.db import connection as db_conn

    # Each thread needs its own DB connection
    try:
        job = PredictionJob.objects.get(id=job_id)
        job.status = PredictionJob.STATUS_RUNNING
        job.save(update_fields=['status', 'updated_at'])

        from ml_engine import predict_url
        result, accuracies = predict_url(job.url)

        # Persist the URLPrediction record
        URLPrediction.objects.create(
            user=job.user,
            url=job.url,
            result=result,
        )

        job.result     = result
        job.accuracies = accuracies
        job.status     = PredictionJob.STATUS_DONE
        job.save(update_fields=['result', 'accuracies', 'status', 'updated_at'])
        logger.info(f"Job {job_id} complete: {result}")

    except Exception as exc:
        logger.exception(f"Job {job_id} failed: {exc}")
        try:
            job = PredictionJob.objects.get(id=job_id)
            job.status    = PredictionJob.STATUS_ERROR
            job.error_msg = str(exc)
            job.save(update_fields=['status', 'error_msg', 'updated_at'])
        except Exception:
            pass
    finally:
        db_conn.close()   # return connection to pool


# ─────────────────────────────────────────────────────────────────────────────
# Public views
# ─────────────────────────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    total_checks    = URLPrediction.objects.count()
    phishing_caught = URLPrediction.objects.filter(result='Phishing').count()
    total_users     = User.objects.filter(is_staff=False).count()
    return render(request, 'landing.html', {
        'total_checks':   total_checks,
        'phishing_caught': phishing_caught,
        'total_users':    total_users,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'RUser/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('dashboard')

        try:
            User.objects.get(username=username)
            messages.error(request, 'Incorrect password. Please try again.')
        except User.DoesNotExist:
            messages.error(request, f'No account found for "{username}". Please register first.')

    return render(request, 'RUser/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone':   form.cleaned_data.get('phone', ''),
                    'country': form.cleaned_data.get('country', ''),
                    'state':   form.cleaned_data.get('state', ''),
                    'city':    form.cleaned_data.get('city', ''),
                }
            )
            # Authenticate properly so backend is attached
            auth_user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1'],
            )
            if auth_user:
                login(request, auth_user)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)

            messages.success(request, f'Welcome, {user.username}! Your account is ready.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'RUser/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing')


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user_predictions = URLPrediction.objects.filter(user=request.user)
    total            = user_predictions.count()
    phishing_count   = user_predictions.filter(result='Phishing').count()
    safe_count       = user_predictions.filter(result='Non Phishing').count()
    recent           = user_predictions[:6]
    phishing_pct     = round((phishing_count / total * 100), 1) if total > 0 else 0

    return render(request, 'RUser/dashboard.html', {
        'total':              total,
        'phishing_count':     phishing_count,
        'safe_count':         safe_count,
        'phishing_pct':       phishing_pct,
        'recent_predictions': recent,
    })


@ajax_login_required
def predict_url_view(request):
    """
    POST — creates a PredictionJob, starts a background thread,
           returns the job_id immediately so the client can poll.
    GET  — renders the predict page.
    """
    if request.method == 'POST':
        url_text = request.POST.get('url', '').strip()

        if not url_text:
            return JsonResponse({'success': False, 'error': 'Please enter a URL.'}, status=400)

        if len(url_text) > 2000:
            return JsonResponse({'success': False, 'error': 'URL too long (max 2000 chars).'}, status=400)

        # Create job record
        job = PredictionJob.objects.create(user=request.user, url=url_text)

        # Kick off background thread
        t = threading.Thread(
            target=_run_prediction_job,
            args=(job.id,),
            daemon=True,
            name=f"pred-{job.id}"
        )
        t.start()

        return JsonResponse({
            'success':  True,
            'job_id':   str(job.id),
            'status':   job.status,
        })

    return render(request, 'RUser/predict.html')


@ajax_login_required
def predict_status(request, job_id):
    """
    GET — returns current status of a PredictionJob.
    Polled every 3 seconds by the frontend.
    """
    try:
        job = PredictionJob.objects.get(id=job_id, user=request.user)
    except PredictionJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found.'}, status=404)

    response = {
        'job_id':  str(job.id),
        'status':  job.status,
        'url':     job.url,
    }

    if job.status == PredictionJob.STATUS_DONE:
        response.update({
            'result':           job.result,
            'is_phishing':      job.is_phishing,
            'model_accuracies': job.accuracies,
            'checked_at':       job.updated_at.strftime('%b %d, %Y at %H:%M'),
        })
    elif job.status == PredictionJob.STATUS_ERROR:
        response['error'] = job.error_msg or 'An unknown error occurred.'

    return JsonResponse(response)


@login_required
def history(request):
    filter_type = request.GET.get('filter', 'all')
    predictions = URLPrediction.objects.filter(user=request.user)

    if filter_type == 'phishing':
        predictions = predictions.filter(result='Phishing')
    elif filter_type == 'safe':
        predictions = predictions.filter(result='Non Phishing')

    return render(request, 'RUser/history.html', {
        'predictions': predictions,
        'filter_type': filter_type,
        'total':       predictions.count(),
    })


@login_required
def profile(request):
    try:
        profile_obj = request.user.profile
    except UserProfile.DoesNotExist:
        profile_obj = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        profile_obj.phone   = request.POST.get('phone', '')
        profile_obj.country = request.POST.get('country', '')
        profile_obj.state   = request.POST.get('state', '')
        profile_obj.city    = request.POST.get('city', '')
        profile_obj.save()

        email = request.POST.get('email', '').strip()
        if email and email != request.user.email:
            request.user.email = email
            request.user.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    user_stats = {
        'total':    URLPrediction.objects.filter(user=request.user).count(),
        'phishing': URLPrediction.objects.filter(user=request.user, result='Phishing').count(),
        'safe':     URLPrediction.objects.filter(user=request.user, result='Non Phishing').count(),
    }

    return render(request, 'RUser/profile.html', {
        'profile':    profile_obj,
        'user_stats': user_stats,
    })
