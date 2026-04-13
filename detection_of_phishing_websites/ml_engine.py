"""
ML Engine — PhishGuard
Core machine learning logic extracted from views for clean separation.
Keeps all original algorithms: Naive Bayes, SVM, Logistic Regression,
Decision Tree, SGD Classifier, Random Forest + VotingClassifier ensemble.
"""
import os
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn import svm
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score
from django.conf import settings


def _get_csv_path():
    return str(settings.DATASET_PATH)


def train_all_models():
    """
    Train all ML models on the URL dataset.
    Returns (accuracy_dict, voting_classifier, count_vectorizer)
    """
    data = pd.read_csv(_get_csv_path())
    mapping = {'Phishing': 0, 'Non Phishing': 1}
    data['Results'] = data['Label'].map(mapping)

    x_raw = data['URL']
    y = data['Results']

    cv = CountVectorizer()
    x_vec = cv.fit_transform(x_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        x_vec, y, test_size=0.20, random_state=42
    )

    accuracy_results = {}
    voting_models = []

    # ── Naive Bayes ──────────────────────────────────────────────
    nb = MultinomialNB()
    nb.fit(X_train, y_train)
    nb_acc = accuracy_score(y_test, nb.predict(X_test)) * 100
    accuracy_results['Naive Bayes'] = round(nb_acc, 2)
    voting_models.append(('naive_bayes', nb))

    # ── Support Vector Machine ───────────────────────────────────
    lin_svm = svm.LinearSVC(max_iter=2000)
    lin_svm.fit(X_train, y_train)
    svm_acc = accuracy_score(y_test, lin_svm.predict(X_test)) * 100
    accuracy_results['SVM'] = round(svm_acc, 2)
    voting_models.append(('svm', lin_svm))

    # ── Logistic Regression ──────────────────────────────────────
    lr = LogisticRegression(random_state=0, solver='lbfgs', max_iter=1000)
    lr.fit(X_train, y_train)
    lr_acc = accuracy_score(y_test, lr.predict(X_test)) * 100
    accuracy_results['Logistic Regression'] = round(lr_acc, 2)
    voting_models.append(('logistic', lr))

    # ── Decision Tree ────────────────────────────────────────────
    dtc = DecisionTreeClassifier(random_state=42)
    dtc.fit(X_train, y_train)
    dtc_acc = accuracy_score(y_test, dtc.predict(X_test)) * 100
    accuracy_results['Decision Tree'] = round(dtc_acc, 2)
    voting_models.append(('decision_tree', dtc))

    # ── SGD Classifier ───────────────────────────────────────────
    sgd = SGDClassifier(loss='hinge', penalty='l2', random_state=0, max_iter=1000)
    sgd.fit(X_train, y_train)
    sgd_acc = accuracy_score(y_test, sgd.predict(X_test)) * 100
    accuracy_results['SGD Classifier'] = round(sgd_acc, 2)
    voting_models.append(('sgd', sgd))

    # ── Random Forest (accuracy tracking only, not in voting) ────
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    rf_acc = accuracy_score(y_test, rf.predict(X_test)) * 100
    accuracy_results['Random Forest'] = round(rf_acc, 2)

    # ── Voting Ensemble (all 5 above) ────────────────────────────
    voting_clf = VotingClassifier(voting_models)
    voting_clf.fit(X_train, y_train)

    return accuracy_results, voting_clf, cv


def predict_url(url_text):
    """
    Predict whether a URL is Phishing or Non Phishing.
    Returns (label: str, model_accuracies: dict)
    """
    accuracy_results, voting_clf, cv = train_all_models()

    url_vector = cv.transform([url_text]).toarray()
    raw_prediction = voting_clf.predict(url_vector)[0]

    label = 'Phishing' if raw_prediction == 0 else 'Non Phishing'
    return label, accuracy_results
