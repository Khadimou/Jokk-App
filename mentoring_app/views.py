import json

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from mentoring_app.forms import MatchingForm, MentorForm
from mentoring_app.models import Matching, Response, Notification, Availability
from mentoring_app.utils import calculate_matching_score_optimized
from smart_mentor.utils import generate_questions, evaluate

from .forms import AvailabilityForm

def availability_view(request):
    if request.method == 'POST':
        form = AvailabilityForm(request.POST)
        #print(form)
        if form.is_valid():
            # Extraire les créneaux de disponibilité à partir des données JSON
            availability_slots = request.POST.get('availability_slots')
            if availability_slots:
                try:
                    slots = json.loads(availability_slots)
                    for slot in slots:
                        # Créer un objet Availability pour chaque créneau
                        Availability.objects.create(
                            user=request.user,
                            day_of_week=slot['dayOfWeek'],
                            start_time=slot['startTime'],
                            end_time=slot['endTime']
                        )
                    return redirect('availability_dates')
                except json.JSONDecodeError:
                    # Gérer l'erreur si la chaîne JSON n'est pas valide
                    # Vous pouvez ajouter un message d'erreur ou une logique de gestion d'erreur ici
                    pass
    else:
        form = AvailabilityForm()

    return render(request, 'mentoring_app/is_mentor.html', {'form': form})
def delete_availability(request, slot_id):
    slot = get_object_or_404(Availability, id=slot_id, user=request.user)
    slot.delete()
    return redirect('availability_dates')  # Rediriger vers la vue qui affiche les créneaux

def availability_dates(request):
    availability_slots = Availability.objects.filter(user=request.user)
    return render(request, 'mentoring_app/availability_dates.html',{'availability_slots': availability_slots})

# Create your views here.
def mentoring_page(request):
    return render(request, 'mentoring_app/mentoring_page.html')

def redirect_mentor(request):
    if request.user.is_authenticated:
        if request.user.profile.is_mentor:
            return redirect('my_page')
        else:
            return redirect('mentor_page')
    else:
        # Rediriger vers la page de connexion si l'utilisateur n'est pas connecté
        return redirect('login')

def my_page(request):
    # Obtenez les créneaux de disponibilité de l'utilisateur
    availability_slots = Availability.objects.filter(user=request.user).values(
        'day_of_week', 'start_time', 'end_time'
    )

    # Convertissez les créneaux en format adapté pour FullCalendar
    calendar_events =  json.dumps([
        {
            'start': slot['day_of_week'] + 'T' + str(slot['start_time']),
            'end': slot['day_of_week'] + 'T' + str(slot['end_time']),
            'color': '#28a745'  # Couleur pour les créneaux enregistrés
        }
        for slot in availability_slots
    ])
    return render(request,'mentoring_app/is_mentor.html', {'calendar_events': calendar_events})

def mentee_page(request):
    return render(request, 'mentoring_app/mentee_page.html')

from django.contrib.auth.decorators import login_required
from .models import Mentor
from .forms import MentorForm

from django.shortcuts import render, redirect
from .forms import MentorForm
from .models import Profile

@login_required
def mentor_page(request):
    user_profile = Profile.objects.get(user=request.user)
    try:
        mentor = Mentor.objects.get(profile=user_profile)
        form = MentorForm(request.POST or None, instance=mentor)
    except Mentor.DoesNotExist:
        form = MentorForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        mentor_instance = form.save(commit=False)
        mentor_instance.profile = user_profile
        mentor_instance.save()
        return redirect('register_page')

    return render(request, 'mentoring_app/mentor_page.html', {'form': form})

from django.shortcuts import get_object_or_404

def register_page(request):
    user = request.user
    user_profile = get_object_or_404(Profile, user=user)

    if request.method == 'POST':
        form = MentorForm(request.POST)
        if form.is_valid():
            mentor_instance = form.save(commit=False)
            mentor_instance.profile = user_profile
            mentor_instance.save()

            questions = generate_questions(mentor_instance.Fields, mentor_instance.Degree)
            request.session['questions'] = questions
            return render(request, 'mentoring_app/questions_page.html', {'questions': questions})
    else:
        form = MentorForm()
    return render(request, 'mentoring_app/result_page.html', {'form': form})

# def evaluate_answers(request):
#     if request.method == 'POST':
#         questions = request.session.get('questions', [])
#         user_answers = {question: request.POST.get(f'answer_{index}') for index, question in enumerate(questions, start=1)}
#         print(user_answers)
#
#         # Evaluate the user's answers
#         evaluation_results = evaluate( user_answers)
#
#         score = 0
#         total_questions = len(questions)
#
#         # Increment score for correct answers
#         for question, result in evaluation_results.items():
#             if result == 'correct':
#                 score += 1
#             else:
#                 score += 0
#
#
#         if total_questions > 0:
#             score_out_of_10 = (score / total_questions) * 10
#         else:
#             score_out_of_10 = 0
#
#         # Clear session data
#         if 'questions' in request.session:
#             del request.session['questions']
#
#         messages.success(request, f'You scored {score_out_of_10}/10!')
#         return render(request, 'mentoring_app/result_page.html', {'score': score_out_of_10})
#     return redirect('register_page')

def evaluate_answers(request):
    if request.method == 'POST':
        questions = request.session.get('questions', [])
        user_answers = {question: request.POST.get(f'answer_{index}') for index, question in enumerate(questions, start=1)}
        #print(user_answers)
        return render(request,'mentoring_app/evaluation.html', {'answers':user_answers})
    return redirect('register_page')
def result_page(request):
    # Retrieve the score from the session
    score_out_of_10 = request.session.get('score_out_of_10', 0)

    # Clear the score from the session after retrieving it
    if 'score_out_of_10' in request.session:
        del request.session['score_out_of_10']

    # Render the result page with the score passed in the context
    return render(request, 'mentoring_app/result_page.html', {'score': score_out_of_10})

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

@login_required
def waiting_page(request):
    if request.method == 'POST':
        user = request.user  # Assurez-vous que l'utilisateur est authentifié
        questions = request.session.get('questions', [])

        for key, value in request.POST.items():
            if key.startswith('answer_'):
                question_index = int(key.split('_')[1]) - 1  # Convertir en index (en commençant par 0)
                if question_index < len(questions):
                    question = questions[question_index]
                    response = Response(user=user, question=question, answer=value)
                    response.save()

        return render(request, 'mentoring_app/waiting_page.html')
    return redirect('register_page')


def optim_find(request):
    if request.method == 'POST':
        form = MatchingForm(request.POST)

        if form.is_valid():
            # Access the cleaned data
            domains = form.cleaned_data['Fields']
            diplomas = form.cleaned_data['Degree']
            skills = form.cleaned_data['Skills']
            career = form.cleaned_data['Objectives']
            professions = form.cleaned_data['Job']
            personality = form.cleaned_data['PersonalityDescription']

            user_input = {
                'Fields': [domains],
                'Degree': [diplomas],
                'Skills': [skills],
                'Objectives': [career],
                'Job': [professions],
                'PersonalityDescription': [personality]
            }
            predicted_score_optim = calculate_matching_score_optimized(user_input)

            # Create a new Matching object and save it
            matching = Matching(Fields=domains, Degree=diplomas, Skills=skills, Objectives=career, Job=professions,PersonalityDescription=personality)
            matching.save()
            # Message de succès
            #messages.success(request, 'Here are the best mentors for you:')

            # Stocker le score dans la session pour une utilisation ultérieure
            request.session['predicted_score_optim'] = predicted_score_optim

            # Rediriger ou rendre la page comme souhaité
            return redirect('matching_optim')
    else:
        form = MatchingForm()

    # Vérifier si le score est déjà stocké en session et l'utiliser s'il est disponible
    predicted_score_optim = request.session.get('predicted_score_optim', None)

    return render(request,'mentoring_app/matching.html',{'form':form, 'predicted_score_optim': predicted_score_optim})

def all_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        return render(request, 'all_notifications.html', {'notifications': notifications})
    else:
        # Rediriger vers la page de connexion si l'utilisateur n'est pas connecté
        return redirect('login')
