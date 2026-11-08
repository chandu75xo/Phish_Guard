"""PhishGuard ML engine.

Production inference loads a previously trained artifact. Training is an explicit
operation (normally performed locally with train_models.py), never an automatic
side effect of a web request or application startup.

The five original classifiers and hard-voting ensemble are preserved.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn import svm
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.tree import DecisionTreeClassifier

logger = logging.getLogger(__name__)

ARTIFACT_SCHEMA_VERSION = 1


def normalize_url(url):
    """Normalize URL text consistently during training and prediction."""
    u = str(url).strip().lower()
    for prefix in ('https://', 'http://', 'ftp://'):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    if u.startswith('www.'):
        u = u[4:]
    return u


_cache_lock = threading.RLock()
_cached_cv = None
_cached_clf = None
_cached_acc = None
_cache_ready = False


class ModelArtifactError(RuntimeError):
    """Raised when the trained model artifact is missing or incompatible."""


def _project_settings():
    from django.conf import settings
    return settings


def _get_csv_path() -> Path:
    return Path(_project_settings().DATASET_PATH)


def _get_artifact_path() -> Path:
    settings = _project_settings()
    configured = getattr(settings, 'ML_MODEL_PATH', None)
    if configured:
        return Path(configured)
    return Path(settings.BASE_DIR) / 'ml_artifacts' / 'phishguard_model.joblib'


def _train_components():
    """Train all five classifiers and the voting ensemble from the CSV dataset."""
    logger.info('PhishGuard: starting explicit model training from %s', _get_csv_path())
    csv_path = _get_csv_path()
    if not csv_path.is_file():
        raise FileNotFoundError(f'Training dataset not found: {csv_path}')

    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['URL', 'Label'])
    mapping = {'Phishing': 0, 'Non Phishing': 1}
    data['Results'] = data['Label'].map(mapping)
    data = data.dropna(subset=['Results'])
    data['Results'] = data['Results'].astype(int)

    if data.empty or data['Results'].nunique() != 2:
        raise ValueError("Dataset must contain both 'Phishing' and 'Non Phishing' labels.")

    x_raw = data['URL'].astype(str).map(normalize_url)
    y = data['Results']

    # Keep the existing project feature extraction and split behavior to avoid
    # changing the model's established prediction semantics in this deployment.
    cv = CountVectorizer(max_features=10000)
    x_vec = cv.fit_transform(x_raw)
    X_train, X_test, y_train, y_test = train_test_split(
        x_vec, y, test_size=0.20, random_state=42
    )

    accuracy_results = {}
    voting_models = []

    classifiers = [
        ('naive_bayes', 'Naive Bayes', MultinomialNB()),
        ('svm', 'SVM', svm.LinearSVC(max_iter=2000, dual=True)),
        ('logistic', 'Logistic Regression', LogisticRegression(
            random_state=0, solver='lbfgs', max_iter=1000
        )),
        ('decision_tree', 'Decision Tree', DecisionTreeClassifier(
            random_state=42, max_depth=20
        )),
        ('sgd', 'SGD Classifier', SGDClassifier(
            loss='hinge', penalty='l2', random_state=0, max_iter=1000
        )),
    ]

    for estimator_name, display_name, estimator in classifiers:
        estimator.fit(X_train, y_train)
        accuracy = accuracy_score(y_test, estimator.predict(X_test)) * 100
        accuracy_results[display_name] = round(float(accuracy), 2)
        voting_models.append((estimator_name, estimator))
        logger.info('%s accuracy: %.2f%%', display_name, accuracy)

    # VotingClassifier clones and fits its estimators. This retains the original
    # hard-voting behavior used by the application.
    voting_clf = VotingClassifier(voting_models, voting='hard')
    voting_clf.fit(X_train, y_train)
    logger.info('PhishGuard voting ensemble training completed.')
    return cv, voting_clf, accuracy_results, int(len(data))


def _save_bundle(cv, clf, accuracies, dataset_rows):
    """Atomically persist a trusted, versioned model bundle to disk."""
    artifact_path = _get_artifact_path()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        'schema_version': ARTIFACT_SCHEMA_VERSION,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scikit_learn_version': sklearn.__version__,
        'python_version': os.sys.version.split()[0],
        'dataset_rows': dataset_rows,
        'accuracies': accuracies,
        'vectorizer': cv,
        'classifier': clf,
    }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=artifact_path.name + '.', suffix='.tmp',
            dir=str(artifact_path.parent), delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
        joblib.dump(bundle, temp_path, compress=3)
        os.replace(temp_path, artifact_path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    logger.info('Saved trained model artifact to %s', artifact_path)
    return artifact_path


def train_all_models():
    """Explicitly retrain all models, save the artifact, and refresh this process.

    Used by train_models.py and retained for the existing admin training page.
    Returns (accuracy_results, count_vectorizer, voting_classifier).
    """
    global _cached_cv, _cached_clf, _cached_acc, _cache_ready
    with _cache_lock:
        cv, clf, accuracies, dataset_rows = _train_components()
        artifact_path = _save_bundle(cv, clf, accuracies, dataset_rows)
        _cached_cv, _cached_clf, _cached_acc = cv, clf, accuracies
        _cache_ready = True
        logger.info('Model cache refreshed from newly trained artifact: %s', artifact_path)
    return accuracies, cv, clf


def load_models(force_reload=False):
    """Load the pre-trained bundle into this process's RAM; never trains."""
    global _cached_cv, _cached_clf, _cached_acc, _cache_ready
    if _cache_ready and not force_reload:
        return _cached_cv, _cached_clf, _cached_acc

    with _cache_lock:
        if _cache_ready and not force_reload:
            return _cached_cv, _cached_clf, _cached_acc

        artifact_path = _get_artifact_path()
        if not artifact_path.is_file():
            raise ModelArtifactError(
                f"Trained model artifact is missing: {artifact_path}. "
                "From the repository root, install requirements and run "
                "'python train_models.py', then include ml_artifacts/phishguard_model.joblib "
                "in your deployment. Startup will not train models automatically."
            )

        try:
            bundle = joblib.load(artifact_path)
        except Exception as exc:
            raise ModelArtifactError(
                f'Could not load model artifact {artifact_path}: {exc}'
            ) from exc

        if not isinstance(bundle, dict):
            raise ModelArtifactError('Model artifact has an invalid format. Retrain it locally.')

        if bundle.get('schema_version') != ARTIFACT_SCHEMA_VERSION:
            raise ModelArtifactError(
                'Model artifact schema is incompatible. Run python train_models.py again.'
            )

        artifact_sklearn = bundle.get('scikit_learn_version')
        if artifact_sklearn != sklearn.__version__:
            raise ModelArtifactError(
                f'Model was trained with scikit-learn {artifact_sklearn}, but this '
                f'process has {sklearn.__version__}. Install the pinned requirements '
                'and regenerate the artifact with that same scikit-learn version.'
            )

        cv = bundle.get('vectorizer')
        clf = bundle.get('classifier')
        accuracies = bundle.get('accuracies')
        if cv is None or clf is None or not isinstance(accuracies, dict):
            raise ModelArtifactError('Model artifact is incomplete. Retrain it locally.')

        _cached_cv, _cached_clf, _cached_acc = cv, clf, accuracies
        _cache_ready = True
        logger.info(
            'Loaded pre-trained PhishGuard models from %s (trained %s; sklearn %s)',
            artifact_path, bundle.get('created_at_utc'), artifact_sklearn
        )
        return _cached_cv, _cached_clf, _cached_acc


def get_or_train():
    """Backward-compatible name: load saved models; do not train on requests."""
    return load_models()


def predict_url(url_text):
    """Predict URL text using the already-loaded voting classifier."""
    cv, clf, accuracies = get_or_train()
    # Keep the vectorizer output sparse; sklearn estimators accept sparse matrices.
    url_vector = cv.transform([normalize_url(url_text)])
    raw_prediction = clf.predict(url_vector)[0]
    label = 'Phishing' if int(raw_prediction) == 0 else 'Non Phishing'
    return label, accuracies


def warm_up():
    """Legacy compatibility helper; now loads an artifact and never trains."""
    return load_models()
