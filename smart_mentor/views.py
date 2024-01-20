import datetime
import json
import mimetypes
import time
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import CustomUser  # Adjust the import path according to your project structure
from workgroup.models import WorkGroup
from .models import Profile, OpenAIAssistant, Follow
from .utils import scrape_website, text_to_pdf, upload_to_openai, create_chat_thread, process_message_with_citations, \
    transcribe_file, create_assistant
import os
import docx
import PyPDF2
from django.contrib.auth import login, logout
from .forms import SignUpForm, ProfileForm
from openai import OpenAI
from mentoring_app.models import Notification

client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate
from django.contrib import messages
from .forms import LoginForm


from django.core.files.storage import FileSystemStorage
from django.conf import settings
from PyPDF2 import PdfReader
import os

def terms(request):
    return render(request, 'terms.html')

def my_assistants(request):
    assistants = OpenAIAssistant.objects.filter(user=request.user)
    return render(request, 'smart_mentor/my_assistants.html', {'assistants': assistants})


def handle_text_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def handle_docx_file(file_path):
    doc = docx.Document(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

def handle_pdf_file(file_path):
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text


def scrape_view(request):
    context = {'file_id': None}

    if not request.user.appuser.is_premium:
        return redirect('product_page')
        # Option 2: Afficher un message d'erreur
        #return HttpResponse("This feature is reserved for premium users.", status=403)

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
            #print(file_type)

            text_content = ""
            if file_type and (file_type.startswith('audio') or file_type.startswith('video')):
                text_content = transcribe_file(uploaded_file_path)
                pdf_path = text_to_pdf(text_content, "transcribed_content.pdf")
            elif file_type in ['application/pdf']:
                text_content = handle_pdf_file(uploaded_file_path)
                pdf_path = text_to_pdf(text_content, "uploaded_content.pdf")
            elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                text_content = handle_docx_file(uploaded_file_path)
                pdf_path = text_to_pdf(text_content, "uploaded_content.pdf")
            elif file_type in ['text/plain']:
                text_content = handle_text_file(uploaded_file_path)
                pdf_path = text_to_pdf(text_content, "uploaded_content.pdf")

            # Upload the PDF to OpenAI
            file_id = upload_to_openai(pdf_path)
            context['file_id'] = file_id

            # Clean up the files after uploading
            os.remove(uploaded_file_path)
            os.remove(pdf_path)

    return render(request, 'smart_mentor/scrape.html', context)
#@csrf_exempt
def chat_view(request):
    file_id = request.GET.get('file_id')
    assistant_name = request.GET.get('assistant_name')
    context = {'file_id': file_id, 'error': None, 'messages': request.session.get('messages', [])}
    if OpenAIAssistant.objects.filter(name=assistant_name).exists():
        context['error'] = 'An assistant with this name already exists. Please choose a different name.'
        return render(request, 'smart_mentor/scrape.html', context)

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
                user = request.user
                # If no assistant exists for this file_id, create a new one
                if user.is_authenticated:
                    assistant_id = create_assistant(user,file_id,assistant_name)
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
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def clear_chat(request):
    if request.method == 'POST':
        # Logique pour effacer les messages
        request.session['messages'] = []
        return JsonResponse({'status': 'success'})
    else:
        # Assurez-vous de renvoyer une réponse même si la méthode n'est pas POST
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

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

@csrf_exempt
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

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                try:
                    profile = Profile.objects.get(user=user)
                    if profile.first_login:
                        profile.first_login = False
                        profile.save()
                        return redirect('create_profile')
                    else:
                        return redirect('home')
                except Profile.DoesNotExist:
                    return redirect('create_profile')
            else:
                messages.error(request, 'Nom d’utilisateur ou mot de passe incorrect.')
    else:
        form = LoginForm()

    context = {'form': form}
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

from django.shortcuts import get_object_or_404

def profile_view(request, user_id=None):
    if user_id is None:
        user = request.user
    else:
        user = get_object_or_404(CustomUser, pk=user_id)
    profile = get_object_or_404(Profile, user=user)
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

def searching(request):
    query = request.GET.get('search', '').strip()
    results = []

    if query:
        # Recherche des groupes de travail
        workgroup_results = WorkGroup.objects.filter(name__icontains=query)

        # Recherche des profils utilisateurs
        profile_results = Profile.objects.filter(
            Q(user__username__icontains=query) |
            Q(bio__icontains=query) |
            Q(skills__icontains=query)
        ).select_related('user')

        for profile in profile_results:
            results.append({
                'type': 'profile',
                'username': profile.user.username,
                'avatar': profile.avatar if profile.avatar else None,
                'bio': profile.bio,
                'social_media_links': profile.social_media_links,
                'id': profile.id,
                # ... autres champs du profil
            })

        # Recherche des assistants
        assistants = OpenAIAssistant.objects.filter(name__icontains=query)
        results += [
            {'type': 'assistant', 'name': assistant.name, 'description': assistant.description}
            for assistant in assistants
        ]

        # Inclusion des workgroups dans les résultats
        results += [
            {
                'type': 'workgroup',
                'id': workgroup.id,
                'name': workgroup.name,
                'description': workgroup.description,
                'avatar': workgroup.avatar if workgroup.avatar else None,
                'creator': workgroup.creator.username
                # ... autres champs du workgroup
            }
            for workgroup in workgroup_results
        ]

    context = {
        'query': query,
        'results': results
    }

    return render(request, 'search_results.html', context)




from rest_framework import viewsets
from .models import Message
from .serializers import MessageSerializer
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Obtenir l'utilisateur actuel
        user = self.request.user

        # Filtrer les messages où l'utilisateur est soit l'expéditeur soit le destinataire
        return self.queryset.filter(Q(sender=user) | Q(recipient=user))


@login_required
def messaging_view(request):
    User = get_user_model()
    users = User.objects.exclude(id=request.user.id)
    messages = Message.objects.filter(recipient=request.user)
    # Récupérer les followers de l'utilisateur connecté
    user_followers = Follow.objects.filter(followed=request.user).select_related('follower')

    # Préparer les données pour le template
    followers_data = [{
        'username': follower.follower.username,
        'profile_picture_url': follower.follower.profile.avatar.url,  # Assurez-vous que cette propriété existe
        'user_id': follower.follower.id
    } for follower in user_followers]

    conversations = {}
    for message in messages:
        username = message.sender.username
        user_id = message.sender.id
        if username not in conversations:
            conversations[username] = {
                'user_id': user_id,
                'profile_picture_url': message.sender.profile.avatar.url if message.sender.profile.avatar else '',
                'last_message': message.text,
                'timestamp': message.sent_at  # Gardez-le comme objet datetime
            }
        else:
            # Comparez les objets datetime avant de formater pour l'affichage
            if message.sent_at > conversations[username]['timestamp']:
                conversations[username]['last_message'] = message.text
                conversations[username]['timestamp'] = message.sent_at  # Toujours un objet datetime

    for username, details in conversations.items():
        # Ajoutez une ligne pour vérifier s'il y a des messages non lus dans cette conversation
        details['has_unread_messages'] = Message.objects.filter(
            sender__username=username,
            recipient=request.user,
            read=False
        ).exists()
        details['timestamp'] = details['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    # Tri par timestamp du dernier message (maintenant une chaîne)
    sorted_conversations = sorted(conversations.items(), key=lambda kv: kv[1]['timestamp'], reverse=True)

    context = {
        'users': users,
        'conversations': sorted_conversations,
        'followers': followers_data  
    }
    return render(request, 'messaging.html', context)

@login_required
def get_messages(request, username):
    User = get_user_model()
    current_user = request.user
    other_user = get_object_or_404(User, username=username)

    messages = Message.objects.filter(
        models.Q(sender=current_user, recipient=other_user) |
        models.Q(sender=other_user, recipient=current_user)
    ).order_by('sent_at')

    def get_avatar_url(user):
        profile = Profile.objects.get(user=user)
        return profile.avatar.url if profile.avatar else ''

    messages_data = [{
        'id': message.id,
        'text': message.text,
        'timestamp': message.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
        'sender_username': message.sender.username,
        'recipient_username': message.recipient.username,
        'sender_profile_picture_url': get_avatar_url(message.sender),
        'recipient_profile_picture_url': get_avatar_url(message.recipient),
        'is_current_user_sender': message.sender == current_user,
        'is_read': message.read,
    } for message in messages]

    return JsonResponse({'messages': messages_data})


@login_required
def get_conversations(request):
    users = User.objects.exclude(id=request.user.id)
    messages = Message.objects.filter(recipient=request.user)

    conversations = {}
    for message in messages:
        username = message.sender.username
        if username not in conversations:
            conversations[username] = {
                'profile_picture_url': message.sender.profile.avatar.url if message.sender.profile.avatar else '',
                'last_message': message.text,
                'timestamp': message.sent_at
            }
        else:
            if message.sent_at > conversations[username]['timestamp']:
                conversations[username]['last_message'] = message.text
                conversations[username]['timestamp'] = message.sent_at

    # Conversion du dictionnaire en tableau d'objets
    conversations_list = [
        {
            'username': username,
            'profile_picture_url': details['profile_picture_url'],
            'last_message': details['last_message'],
            'timestamp': details['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        }
        for username, details in conversations.items()
    ]

    # Tri par timestamp du dernier message
    sorted_conversations = sorted(conversations_list, key=lambda k: k['timestamp'], reverse=True)

    # Retourne les données en JSON
    return JsonResponse({'conversations': sorted_conversations})


@login_required
def message_details(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    # Obtenez l'URL de l'image du profil (adaptez selon la structure de votre modèle)
    profile_picture_url = message.sender.profile.avatar.url if message.sender.profile.avatar else ''
    data = {
        'sender': message.sender.username,
        'senderId': message.sender.id,  # Ajouter l'ID de l'expéditeur
        'content': message.text,
        'timestamp': message.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
        'profile_picture_url': request.build_absolute_uri(profile_picture_url)
        # Autres champs si nécessaire
    }
    return JsonResponse(data)

from rest_framework.views import APIView
from django.contrib.auth.models import User
from .serializers import UserSerializer

class SearchUsersAPIView(APIView):
    """
    View to search for users by username.
    """

    def get(self, request, format=None):
        query = request.query_params.get('q', None)
        if query is not None:
            users = User.objects.filter(username__icontains=query)
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        return Response({"message": "Search query not provided"}, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.decorators import api_view

@login_required
def sendMessage(request):
    User = get_user_model()
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        message_text = request.POST.get('message_text')
        sender = request.user

        try:
            recipient = User.objects.get(pk=recipient_id)
            sender_profile = get_object_or_404(Profile, user=sender)
            avatar_url = sender_profile.avatar.url if sender_profile.avatar else None

            message = Message(sender=sender, recipient=recipient, text=message_text)
            message.save()
            messages.success(request, 'Message sent successfully.')
            # You might want to include the avatar URL in the success message or pass it to the template
            return redirect('messaging')
        except User.DoesNotExist:
            messages.error(request, 'Invalid recipient ID.')
        except Exception as e:
            messages.error(request, f'Error sending message: {e}')

    return redirect('home')


@api_view(['POST'])
def send_message(request):
    # Récupérer les données de la requête
    sender = request.user
    recipient_id = request.data.get('recipient')
    text = request.data.get('text')

    # Vérifier si le destinataire existe
    try:
        recipient = User.objects.get(pk=recipient_id)
    except User.DoesNotExist:
        return Response({'error': 'Invalid recipient ID'}, status=status.HTTP_400_BAD_REQUEST)

    # Créer et sauvegarder le nouveau message
    message = Message(sender=sender, recipient=recipient, text=text)
    message.save()

    # Sérialiser et retourner le nouveau message
    serializer = MessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

@require_POST
def send_reply(request):
    User = get_user_model()
    data = json.loads(request.body)
    message_text = data.get('text')
    recipient_id = data.get('recipientId')  # ID du destinataire

    try:
        sender = request.user  # L'expéditeur est l'utilisateur actuellement connecté
        recipient = User.objects.get(pk=recipient_id)

        new_message = Message.objects.create(
            sender=sender,
            recipient=recipient,
            text=message_text,
            sent_at=now(),
            read=False
        )

        return JsonResponse({'status': 'success', 'message_id': new_message.id})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Recipient not found'}, status=400)

@login_required
def get_unread_messages_count(request):
    unread_count = Message.objects.filter(recipient=request.user, read=False).count()
    return JsonResponse({'unread_count': unread_count})

@require_POST
def mark_message_as_read(request, message_id):
    try:
        message = Message.objects.get(id=message_id, recipient=request.user)
        message.read = True
        message.save()
        return JsonResponse({'status': 'success'})
    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)

@require_POST
@login_required
def mark_conversation_as_read(request, username):
    User = get_user_model()
    recipient = request.user
    sender = User.objects.get(username=username)

    # Marquez tous les messages non lus de cette conversation comme lus
    Message.objects.filter(sender=sender, recipient=recipient, read=False).update(read=True)

    return JsonResponse({'status': 'success'})
def get_user_info(request):
    User = get_user_model()
    username = request.GET.get('username', None)
    if username:
        try:
            user = User.objects.get(username=username)
            profile_picture_url = user.profile.avatar.url if user.profile.avatar else None

            return JsonResponse({
                'status': 'success',
                'username': user.username,
                'profile_picture_url': profile_picture_url
            })
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def get_user_id(request):
    User = get_user_model()
    username = request.GET.get('username')
    if username:
        try:
            user = User.objects.get(username=username)
            return JsonResponse({'status': 'success', 'user_id': user.id})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})
    return JsonResponse({'status': 'error', 'message': 'Username not provided'})


@login_required
@require_POST
def follow_toggle(request):
    User = get_user_model()
    user_id = request.POST.get('user_id')
    try:
        followed_user = User.objects.get(pk=user_id)
        follow, created = Follow.objects.get_or_create(follower=request.user, followed=followed_user)

        if not created:
            follow.delete()
            followed = False
        else:
            followed = True

        return JsonResponse({'status': 'ok', 'followed': followed})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
