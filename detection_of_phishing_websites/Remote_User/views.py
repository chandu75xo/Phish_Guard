import json
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods

from .models import UserProfile, URLPrediction, ModelAccuracy
from .forms import RegisterForm


# ─────────────────────────────────────────────────────────
# Public views
# ─────────────────────────────────────────────────────────

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    total_checks = URLPrediction.objects.count()
    phishing_caught = URLPrediction.objects.filter(result='Phishing').count()
    total_users = User.objects.filter(is_staff=False).count()
    return render(request, 'landing.html', {
        'total_checks': total_checks,
        'phishing_caught': phishing_caught,
        'total_users': total_users,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'RUser/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                phone=form.cleaned_data.get('phone', ''),
                country=form.cleaned_data.get('country', ''),
                state=form.cleaned_data.get('state', ''),
                city=form.cleaned_data.get('city', ''),
            )
            login(request, user)
            messages.success(request, f'Welcome to PhishGuard, {user.username}!')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'RUser/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing')


# ─────────────────────────────────────────────────────────
# Authenticated user views
# ─────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    user_predictions = URLPrediction.objects.filter(user=request.user)
    total = user_predictions.count()
    phishing_count = user_predictions.filter(result='Phishing').count()
    safe_count = user_predictions.filter(result='Non Phishing').count()
    recent = user_predictions[:6]
    phishing_pct = round((phishing_count / total * 100), 1) if total > 0 else 0

    return render(request, 'RUser/dashboard.html', {
        'total': total,
        'phishing_count': phishing_count,
        'safe_count': safe_count,
        'phishing_pct': phishing_pct,
        'recent_predictions': recent,
    })


@login_required
def predict_url_view(request):
    if request.method == 'POST':
        url_text = request.POST.get('url', '').strip()

        if not url_text:
            return JsonResponse({'error': 'Please enter a URL to check.'}, status=400)

        if len(url_text) > 2000:
            return JsonResponse({'error': 'URL is too long (max 2000 characters).'}, status=400)

        try:
            from ml_engine import predict_url
            result, model_accuracies = predict_url(url_text)

            prediction = URLPrediction.objects.create(
                user=request.user,
                url=url_text,
                result=result,
            )

            return JsonResponse({
                'success': True,
                'result': result,
                'is_phishing': result == 'Phishing',
                'url': url_text,
                'model_accuracies': model_accuracies,
                'prediction_id': prediction.id,
                'checked_at': prediction.checked_at.strftime('%b %d, %Y at %H:%M'),
            })

        except FileNotFoundError:
            return JsonResponse({
                'error': 'Dataset file not found. Please contact the administrator.'
            }, status=500)
        except Exception as e:
            return JsonResponse({'error': f'Prediction failed: {str(e)}'}, status=500)

    return render(request, 'RUser/predict.html')


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
        'total': predictions.count(),
    })


@login_required
def profile(request):
    try:
        profile_obj = request.user.profile
    except UserProfile.DoesNotExist:
        profile_obj = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        profile_obj.phone = request.POST.get('phone', '')
        profile_obj.country = request.POST.get('country', '')
        profile_obj.state = request.POST.get('state', '')
        profile_obj.city = request.POST.get('city', '')
        profile_obj.save()

        email = request.POST.get('email', '').strip()
        if email:
            request.user.email = email
            request.user.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    user_stats = {
        'total': URLPrediction.objects.filter(user=request.user).count(),
        'phishing': URLPrediction.objects.filter(user=request.user, result='Phishing').count(),
        'safe': URLPrediction.objects.filter(user=request.user, result='Non Phishing').count(),
    }

    return render(request, 'RUser/profile.html', {
        'profile': profile_obj,
        'user_stats': user_stats,
    })
