from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

from .models import Mentor



def calculate_matching_score_optimized(mentore):
    weights = {
        'Fields': 0.9,
        'Degree': 0.9,
        'Skills': 0.9,
        'Objectives': 0.9,
        'Job': 0.9,
        'PersonalityDescription': 1
    }

    # Préparez les textes des mentores pour la vectorisation
    mentore_texts = [str(mentore[col]) for col in weights.keys()]
    # Initialisez le vectorizer une seule fois et réutilisez-le
    vectorizer = TfidfVectorizer()
    vectorizer.fit(mentore_texts)  # Fit une seule fois sur les textes du mentore
    mentore_vectors = vectorizer.transform(mentore_texts)

    top_mentors = []  # Liste pour stocker les meilleurs mentors avec leurs scores

    mentors = Mentor.objects.all()  # Récupérer tous les objets de mentor depuis la base de données
    for mentor in mentors:
        mentor_texts = [str(getattr(mentor, col)) for col in weights.keys()]
        mentor_vectors = vectorizer.transform(mentor_texts)

        # Calcul de la similarité cosinus pour tous les champs en une seule fois
        similarity_scores = cosine_similarity(mentor_vectors, mentore_vectors)

        # Calcul du score global pondéré pour ce mentor
        weighted_scores = similarity_scores.diagonal() * np.array(list(weights.values()))
        matching_score = np.mean(weighted_scores)

        # Ajoutez le mentor et son score dans la liste
        top_mentors.append((matching_score, mentor))

    # Triez les mentors en fonction de leur score de manière décroissante
    top_mentors.sort(reverse=True, key=lambda x: x[0])

    # Sélectionnez les 3 meilleurs scores et leurs informations associées
    top_3_mentors = top_mentors[:3]
    top_3_mentors_info = [{
        'Score': score,
        'FirstName': mentor.profile.user.first_name,  # Accès à first_name via User
        'LastName': mentor.profile.user.last_name,
        'Skills': mentor.Skills,
        'Job': mentor.Job,
        #'Rating': mentor.Rating,
        'ID': mentor.profile.user.id
    } for score, mentor in top_3_mentors]

    return top_3_mentors_info
