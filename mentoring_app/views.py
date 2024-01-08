from django.contrib import messages
from django.shortcuts import render, redirect

from mentoring_app.forms import MatchingForm, MentorForm
from mentoring_app.models import Matching, Response, Notification
from mentoring_app.utils import calculate_matching_score_optimized
from smart_mentor.utils import generate_questions, evaluate


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
    return render(request,'mentoring_app/is_mentor.html')

def mentee_page(request):
    return render(request, 'mentoring_app/mentee_page.html')

def mentor_page(request):
    if request.method == 'POST':
        form = MentorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('register_page')
    else:
        form = MentorForm()

    return render(request, 'mentoring_app/mentor_page.html', {'form': form})

def register_page(request):
    if request.method == 'POST':
        form = MentorForm(request.POST)
        if form.is_valid():
            fields = form.cleaned_data['Fields']
            degree = form.cleaned_data['Degree']

            form.save()
            questions = generate_questions(fields, degree)

            # Store questions and answers in the session
            request.session['questions'] = questions

            return render(request, 'mentoring_app/questions_page.html', {'questions': questions})
    else:
        form = MentorForm()
    return render(request, 'mentoring_app/register_page.html', {'form': form})

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
