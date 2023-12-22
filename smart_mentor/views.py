import datetime
import mimetypes
import time

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import Profile, OpenAIAssistant
from .utils import scrape_website, text_to_pdf, upload_to_openai, create_chat_thread, process_message_with_citations, \
    transcribe_file, create_assistant
import os
import openai
from django.http import JsonResponse
from django.contrib.auth import login, logout
from .forms import SignUpForm, ProfileForm
from openai import OpenAI


client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate
from django.contrib import messages
from .forms import LoginForm


from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

def scrape_view(request):
    context = {'file_id': None}
    if request.method == "POST":
        # Handle URL scraping
        if 'scrape' in request.POST:
            url = request.POST.get('website_url')
            scraped_text = scrape_website(url)
            pdf_path = text_to_pdf(scraped_text, "scraped_content.pdf")
            file_id = upload_to_openai(pdf_path)
            context['file_id'] = file_id
            os.remove(pdf_path)
        # Handle file upload
        elif 'upload' in request.POST and request.FILES:
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            uploaded_file_path = os.path.join(settings.MEDIA_ROOT, filename)

            # Determine the file type
            file_type, _ = mimetypes.guess_type(uploaded_file_path)

            if file_type.startswith('audio') or file_type.startswith('video'):
                # It's an audio or video file, transcribe it
                text_content = transcribe_file(uploaded_file_path)
                pdf_path = text_to_pdf(text_content, "transcribed_content.pdf")
            else:
                # It's not an audio or video file, process it as a text file
                # (Or handle other file types as necessary)
                pdf_path = text_to_pdf(uploaded_file_path, "uploaded_content.pdf")

            # Upload the PDF to OpenAI
            file_id = upload_to_openai(pdf_path)
            context['file_id'] = file_id

            # Clean up the files after uploading
            os.remove(uploaded_file_path)
            os.remove(pdf_path)

    return render(request, 'smart_mentor/scrape.html', context)

@csrf_exempt
def chat_view(request):
    file_id = request.GET.get('file_id')
    messages = request.session.get('messages', [])
    context = {'error': None, 'response': None, 'messages': messages, 'file_id': file_id}

    if request.method == "POST":
        user_message = request.POST.get('message')
        thread_id = None

        if not thread_id:
            thread_id = create_chat_thread(file_id)
            request.session['thread_id'] = thread_id

        try:
            # Send user message to the thread
            client.beta.threads.messages.create(thread_id=thread_id, role="user", content=user_message)

            # Trigger the assistant's response
            # Check if an assistant for this file_id already exists
            try:
                assistant = OpenAIAssistant.objects.get(file_id=file_id)
                assistant_id = assistant.assistant_id
            except OpenAIAssistant.DoesNotExist:
                # If no assistant exists for this file_id, create a new one
                assistant_id = create_assistant(file_id)
                # Note: create_assistant function should save the new assistant in the database

            run = client.beta.threads.runs.create(
                assistant_id=assistant_id,
                thread_id=thread_id
            )


            # Code to wait for run completion
           # print(run.model_dump_json(indent=4))

            while True:
                # Wait for 5 seconds
                time.sleep(5)

                # Retrieve the run status
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                #print(run_status.model_dump_json(indent=4))

                # If run is completed, get messages
                if run_status.status == 'completed':

                    # Loop through messages and print content based on role
                    # Convertir les messages en une structure sérialisable
                    messages = client.beta.threads.messages.list(thread_id=thread_id).data
                    serializable_messages = [
                        {
                            'role': msg.role,
                            'content': msg.content[0].text.value,
                            "timestamp": datetime.datetime.fromtimestamp(msg.created_at).strftime("%Y-%m-%d %H:%M:%S")
                        }
                        for msg in messages
                    ]

                    # Inverser l'ordre des messages
                    serializable_messages.reverse()

                    request.session['messages'] = serializable_messages

                    #print(serializable_messages)

                    break
                elif run_status.status == 'requires_action':
                    print("Function Calling")
                    required_actions = run_status.required_action.submit_tool_outputs.model_dump()
                    print(required_actions)
                    tool_outputs = []
                    import json
                    for action in required_actions["tool_calls"]:
                        func_name = action['function']['name']
                        arguments = json.loads(action['function']['arguments'])

                        if func_name == "get_stock_price":
                            output = upload_to_openai(symbol=arguments['symbol'])
                            tool_outputs.append({
                                "tool_call_id": action['id'],
                                "output": output
                            })
                        else:
                            raise ValueError(f"Unknown function: {func_name}")

                    print("Submitting outputs back to the Assistant...")
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                else:
                    print("Waiting for the Assistant to process...")
                    time.sleep(5)

            context = {
                'messages': request.session.get('messages', []),
                'file_id': file_id,
                'error': None
            }

        except Exception as e:
            context['error'] = f"An error occurred: {str(e)}"

    return render(request, 'smart_mentor/chat.html', context)


def home(request):
    context = {}
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            context['user_profile'] = profile
        except Profile.DoesNotExist:
            pass

    return render(request, 'home.html', context)

def change_theme(request):
    if request.method == 'POST':
        # Ajustez les valeurs pour correspondre à ce que la fonction JavaScript envoie
        theme = request.POST.get('displayPanel', 'light')
        if theme == 'dark':
            request.session['theme'] = 'dark-mode'
            print(request.session['theme'])
        else:
            request.session['theme'] = 'light-mode'
            print(request.session['theme'])

        return JsonResponse({"theme": request.session['theme']})
    else:
        return JsonResponse({"error": "Invalid request"}, status=400)
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            # messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def account_settings(request):
    # Logique pour afficher et gérer les paramètres du compte
    return render(request, 'delete_account.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        # Traiter la suppression du compte
        user = request.user
        user.delete()  # Supprimer l'utilisateur et toutes ses données associées

        # Déconnecter l'utilisateur après la suppression du compte
        logout(request)

        # Afficher un message indiquant que le compte a été supprimé
        messages.success(request, "Votre compte a été supprimé avec succès.")

        # Rediriger vers la page d'accueil ou une autre page appropriée
        return redirect('login')

    # Si la méthode n'est pas POST, rediriger vers une page de confirmation ou une page d'erreur
    return render(request, 'confirm_delete_account.html')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Vérifiez si l'utilisateur a déjà un profil
                try:
                    Profile.objects.get(user=user)
                    # Si un profil existe, redirigez vers 'home'
                    return redirect('home')
                except Profile.DoesNotExist:
                    # S'il n'y a pas de profil, redirigez vers 'create_profile'
                    return redirect('create_profile')
            else:
                messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect.')
    else:
        form = LoginForm()

    context = {
        'form': form
    }
    return render(request, 'default.html', context)

def logout_view(request):
    logout(request)
    # Rediriger vers la page d'accueil après la déconnexion
    return redirect('login')

@login_required
def create_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('home')
    else:
        form = ProfileForm()

    return render(request, 'create_profile.html', {'form': form})

def profile_view(request, user_id):
    profile = Profile.objects.get(user_id=user_id)
    return render(request, 'profile.html', {'profile': profile})

@login_required
def edit_profile(request):
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile', user_id=request.user.id)
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'edit_profile.html', {'form': form})


def search_view(request):
    query = request.GET.get('search', '').strip()
    if query:
        # Filter profiles based on the username of the related User
        results = Profile.objects.filter(user__username__icontains=query)
    else:
        results = Profile.objects.none()

    context = {
        'results': results,
        'query': query
    }
    return render(request, 'search_results.html', context)

