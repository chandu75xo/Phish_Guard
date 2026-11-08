"""Train PhishGuard locally and create the deployable model artifact.

Run from the repository root:
    python train_models.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / 'detection_of_phishing_websites'
sys.path.insert(0, str(APP_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'detection_of_phishing_websites.settings')

import django  # noqa: E402

django.setup()

from ml_engine import train_all_models  # noqa: E402


def main():
    print('Starting local PhishGuard model training.')
    print('This trains five classifiers and the hard-voting ensemble.')
    accuracies, _, _ = train_all_models()
    print('\nTraining completed. Holdout accuracies:')
    for name, accuracy in accuracies.items():
        print(f'  {name}: {accuracy:.2f}%')
    artifact = APP_DIR / 'ml_artifacts' / 'phishguard_model.joblib'
    print(f'\nSaved model artifact: {artifact}')
    print('Include this file in your Git commit/deployment.')


if __name__ == '__main__':
    main()
