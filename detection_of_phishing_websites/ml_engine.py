"""
ML Engine — PhishGuard
Trains once on startup and caches models in memory.
All 5 original algorithms preserved. Random Forest removed
from training (it was never in the voting ensemble and uses
~200MB on its own — the primary cause of OOM on Render free tier).
"""
import threading
import logging
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn import svm
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score

logger = logging.getLogger(__name__)

# ── In-memory model cache ─────────────────────────────────────────────────────
_cache_lock    = threading.Lock()
_cached_cv     = None   # CountVectorizer (fitted on training data)
_cached_clf    = None   # VotingClassifier
_cached_acc    = None   # dict of model accuracies
_cache_ready   = False


def _get_csv_path():
    from django.conf import settings
    return str(settings.DATASET_PATH)


def _train():
    """
    Load data, train all models, cache results.
    Called once on first prediction and then reuses cache.
    """
    global _cached_cv, _cached_clf, _cached_acc, _cache_ready

    logger.info("ML Engine: starting model training...")

    data = pd.read_csv(_get_csv_path())

    # Drop rows with missing values in key columns
    data = data.dropna(subset=['URL', 'Label'])

    mapping = {'Phishing': 0, 'Non Phishing': 1}
    data['Results'] = data['Label'].map(mapping)

    # Drop unmapped rows
    data = data.dropna(subset=['Results'])
    data['Results'] = data['Results'].astype(int)

    x_raw = data['URL'].astype(str)
    y     = data['Results']

    cv    = CountVectorizer(max_features=10000)   # cap features to reduce memory
    x_vec = cv.fit_transform(x_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        x_vec, y, test_size=0.20, random_state=42
    )

    accuracy_results = {}
    voting_models    = []

    # ── Naive Bayes ───────────────────────────────────────────────
    nb = MultinomialNB()
    nb.fit(X_train, y_train)
    nb_acc = accuracy_score(y_test, nb.predict(X_test)) * 100
    accuracy_results['Naive Bayes'] = round(nb_acc, 2)
    voting_models.append(('naive_bayes', nb))
    logger.info(f"  Naive Bayes: {nb_acc:.1f}%")

    # ── SVM ───────────────────────────────────────────────────────
    lin_svm = svm.LinearSVC(max_iter=2000, dual=True)
    lin_svm.fit(X_train, y_train)
    svm_acc = accuracy_score(y_test, lin_svm.predict(X_test)) * 100
    accuracy_results['SVM'] = round(svm_acc, 2)
    voting_models.append(('svm', lin_svm))
    logger.info(f"  SVM: {svm_acc:.1f}%")

    # ── Logistic Regression ───────────────────────────────────────
    lr = LogisticRegression(random_state=0, solver='lbfgs', max_iter=1000)
    lr.fit(X_train, y_train)
    lr_acc = accuracy_score(y_test, lr.predict(X_test)) * 100
    accuracy_results['Logistic Regression'] = round(lr_acc, 2)
    voting_models.append(('logistic', lr))
    logger.info(f"  Logistic Regression: {lr_acc:.1f}%")

    # ── Decision Tree ─────────────────────────────────────────────
    dtc = DecisionTreeClassifier(random_state=42, max_depth=20)
    dtc.fit(X_train, y_train)
    dtc_acc = accuracy_score(y_test, dtc.predict(X_test)) * 100
    accuracy_results['Decision Tree'] = round(dtc_acc, 2)
    voting_models.append(('decision_tree', dtc))
    logger.info(f"  Decision Tree: {dtc_acc:.1f}%")

    # ── SGD Classifier ────────────────────────────────────────────
    sgd = SGDClassifier(loss='hinge', penalty='l2', random_state=0, max_iter=1000)
    sgd.fit(X_train, y_train)
    sgd_acc = accuracy_score(y_test, sgd.predict(X_test)) * 100
    accuracy_results['SGD Classifier'] = round(sgd_acc, 2)
    voting_models.append(('sgd', sgd))
    logger.info(f"  SGD: {sgd_acc:.1f}%")

    # ── Voting Ensemble ───────────────────────────────────────────
    voting_clf = VotingClassifier(voting_models, voting='hard')
    voting_clf.fit(X_train, y_train)
    logger.info("  Voting Ensemble ready.")

    _cached_cv   = cv
    _cached_clf  = voting_clf
    _cached_acc  = accuracy_results
    _cache_ready = True

    logger.info("ML Engine: training complete, models cached.")
    return cv, voting_clf, accuracy_results


def get_or_train():
    """
    Return cached models, training once if not yet done.
    Thread-safe — only one training run happens at a time.
    """
    global _cache_ready
    if _cache_ready:
        return _cached_cv, _cached_clf, _cached_acc

    with _cache_lock:
        # Double-check after acquiring lock
        if _cache_ready:
            return _cached_cv, _cached_clf, _cached_acc
        return _train()


def predict_url(url_text):
    """
    Predict whether a URL is Phishing or Non Phishing.
    Returns (label: str, model_accuracies: dict)
    """
    cv, clf, accuracies = get_or_train()

    url_vector     = cv.transform([str(url_text)]).toarray()
    raw_prediction = clf.predict(url_vector)[0]

    label = 'Phishing' if int(raw_prediction) == 0 else 'Non Phishing'
    return label, accuracies


def warm_up():
    """
    Call this at startup to pre-train models in a background thread
    so the first real prediction request is fast.
    """
    def _warm():
        try:
            get_or_train()
        except Exception as e:
            logger.error(f"ML warm-up failed: {e}")

    t = threading.Thread(target=_warm, daemon=True, name="ml-warmup")
    t.start()
