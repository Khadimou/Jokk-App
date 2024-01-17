import json
from django.contrib.auth import get_user_model
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from mentoring_app.models import Notification
from smart_mentor.models import Profile, OpenAIAssistant
from smart_mentor.utils import create_chat_thread, create_assistant
from workgroup.forms import RevisionForm
from workgroup.models import WorkGroup, WorkGroupMember, ChatRoom, UserOnlineStatus

# Create your views here.
def revision_group(request):
    if request.method == 'POST':
        form = RevisionForm(request.POST)

        if form.is_valid():
            messages.success(request, f'Form created for !')
    else:
        form = RevisionForm()

    return render(request, 'workgroup/create_group.html',{'form':form})

def search_view(request):
    query = request.GET.get('search', '').strip()
    results = []

    if query:
        # Recherche des profils d'utilisateurs dont le nom d'utilisateur contient la requête
        user_profiles = Profile.objects.filter(user__username__icontains=query)

        # Création de la liste des résultats pour les profils utilisateurs
        results = [
            {
                'type': 'profile',
                'username': profile.user.username,
                'avatar': profile.avatar.url if profile.avatar else None,
                'id': profile.user.id  # Ajout de l'ID de l'utilisateur si nécessaire
            }
            for profile in user_profiles
        ]

    return JsonResponse({'results': results})


@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')  # Ajoutez un tri si nécessaire
    notifications_data = [{
        'id': notification.id,
        'title': notification.title,
        'body': notification.body,
        'read': notification.read,  # Ajoutez l'état de lecture
        'type': notification.type,
        'workgroup_id': notification.workgroup_id if notification.workgroup else None
    } for notification in notifications]

    unread_count = notifications.filter(read=False).count()  # Compter uniquement les notifications non lues

    return JsonResponse({'notifications': notifications_data, 'unread_count': unread_count})

@login_required
@require_POST
def send_invitation(request):
    User = get_user_model()
    try:
        data = json.loads(request.body)
        username = data['username']
        user = User.objects.get(username=username)
        workgroup_id = data['workgroup_id']  # Assurez-vous de passer l'ID du groupe de travail
        workgroup = WorkGroup.objects.get(id=workgroup_id)

        # Créer une instance WorkGroupMember avec le statut 'pending'
        WorkGroupMember.objects.create(
            user=user,
            workgroup=workgroup,
            status='pending'
        )

        Notification.objects.create(
            recipient=user,
            workgroup=workgroup,  # Ajout de l'instance WorkGroup à la notification
            title=f'Invitation to join {workgroup.name}',
            body=f'You have been invited to join the workgroup "{workgroup.name}" by {request.user.username}',
            type='invitation',
            read=False
        )

        return JsonResponse({'status': 'success', 'message': 'Invitation sent successfully.'})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User does not exist.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        await self.accept()

        # Envoyer les notifications non lues à l'utilisateur
        notifications = Notification.objects.filter(recipient=self.user, read=False)
        await self.send(json.dumps({
            "notifications": [{"title": n.title, "body": n.body} for n in notifications]
        }))

@login_required
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'})

def get_assistant_for_workgroup(workgroup_id):
    try:
        workgroup = WorkGroup.objects.get(id=workgroup_id)
        # Si le groupe de travail est configuré pour avoir un assistant
        if workgroup.with_assistant:
            # Récupérer le premier assistant associé au groupe de travail
            assistant = workgroup.assistants.first()
            return assistant
    except WorkGroup.DoesNotExist:
        # Gérer le cas où le groupe de travail n'existe pas
        return None

    return None

def workgroup_detail(request, pk):
    workgroup = get_object_or_404(WorkGroup, pk=pk)
    assistant = get_assistant_for_workgroup(pk)
    assistant_name = assistant.name if assistant else None

    # Exclure l'assistant de members_info
    members_info = WorkGroupMember.objects.filter(workgroup=workgroup).exclude(user__username=assistant_name).select_related('user')

    try:
        member = WorkGroupMember.objects.get(workgroup=workgroup, user=request.user)
        is_allowed = member.status in ['pending', 'accepted']
        is_accepted = member.status == 'accepted'
    except WorkGroupMember.DoesNotExist:
        is_allowed = False
        is_accepted = False

    if workgroup.creator == request.user:
        is_allowed = True

    if not is_allowed:
        return HttpResponseForbidden("You are not authorised to view this group.")

    #members_info = WorkGroupMember.objects.filter(workgroup=workgroup).select_related('user')
    chat_rooms = workgroup.chatrooms.all()
    return render(request, 'workgroup/classroom.html', {
        'workgroup': workgroup,
        'members_info': members_info,
        'is_creator': workgroup.creator == request.user,
        'is_accepted': is_accepted,
        'chat_rooms': chat_rooms,
        'assistant_name': assistant_name,
    })

@login_required
@require_POST
def clear_all_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    return JsonResponse({'status': 'success', 'message': 'All notifications cleared.'})

def is_valid_assistant_name(user, name):
    """
    Vérifie si le nom de l'assistant correspond à un assistant existant créé par l'utilisateur.
    """
    return OpenAIAssistant.objects.filter(user=user, name=name).exists()

@csrf_exempt
@login_required
def create_workgroup(request):
    User = get_user_model()

    if request.method == 'POST':
        form = RevisionForm(request.POST, request.FILES)
        if form.is_valid():
            workgroup = form.save(commit=False)
            workgroup.creator = request.user

            # Vérifier si l'assistant doit être ajouté et si le nom est valide
            if 'create_with_assistant' in request.POST:
                assistant_name = request.POST.get('assistant_name', '').strip()
                if not is_valid_assistant_name(request.user, assistant_name):
                    messages.error(request, 'Invalid assistant name. Please check and try again.')
                    return render(request, 'workgroup/create_group.html', {'form': form})

                # Si un assistant est ajouté, mettez à jour with_assistant
                workgroup.with_assistant = True

            workgroup = form.save(commit=False)
            workgroup.creator = request.user
            workgroup.save()
            form.save_m2m()

            # Traitement supplémentaire pour ajouter l'assistant
            if 'create_with_assistant' in request.POST:
                # Récupérer ou créer l'assistant utilisateur
                assistant_user, _ = User.objects.get_or_create(username=assistant_name)
                # Vérifiez si l'assistant est déjà membre du groupe
                if not WorkGroupMember.objects.filter(user=assistant_user, workgroup=workgroup).exists():
                    WorkGroupMember.objects.create(
                        user=assistant_user,
                        workgroup=workgroup,
                        status='accepted'
                    )

                # Associer l'assistant au groupe de travail
                try:
                    assistant = OpenAIAssistant.objects.get(name=assistant_name)
                    workgroup.assistants.add(assistant)
                except OpenAIAssistant.DoesNotExist:
                    # Gérer le cas où l'assistant n'existe pas
                    messages.error(request, f"The assistant '{assistant_name}' does not exist.")
                    return redirect('revision_group')

            messages.success(request, 'Working group successfully set up.')
            return redirect('workgroup_detail', pk=workgroup.pk)
        else:
            messages.error(request, 'Error when creating the workgroup.')
    else:
        form = RevisionForm()

    return render(request, 'workgroup/create_group.html', {'form': form})

def edit_workgroup(request, pk):
    workgroup = get_object_or_404(WorkGroup, pk=pk)
    if request.method == 'POST':
        form = RevisionForm(request.POST, instance=workgroup)
        if form.is_valid():
            form.save()
            return redirect('workgroup_detail', pk=workgroup.pk)
    else:
        form = RevisionForm(instance=workgroup)
    return render(request, 'workgroup/edit_workgroup.html', {'form': form, 'workgroup': workgroup})

# Vue pour lister tous les workgroups
def workgroup_list(request):
    workgroups = WorkGroup.objects.filter(creator=request.user)
    return render(request, 'workgroup/workgroup_list.html', {'workgroups': workgroups})

def delete_workgroup(request, pk):
    workgroup = get_object_or_404(WorkGroup, pk=pk)
    if request.method == 'POST':
        workgroup.delete()
        return redirect('workgroup_list')  # Redirige vers la liste des workgroups
    return render(request, 'workgroup/confirm_delete.html', {'workgroup': workgroup})

def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    workgroup_id = notification.workgroup_id
    return render(request, 'notification_detail.html', {'notification': notification, 'workgroup_id': workgroup_id})

@login_required
def accept_join(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    if not notification.workgroup:
        return JsonResponse({'status': 'error', 'message': 'Invalid notification.'})

    # Ici, utilisez le sender de la notification comme l'utilisateur à ajouter au groupe
    workgroup_member, created = WorkGroupMember.objects.get_or_create(
        user=notification.sender,
        workgroup=notification.workgroup
    )

    if request.user != workgroup_member.workgroup.creator:
        return HttpResponseForbidden("You are not authorized to accept this join request.")

    workgroup_member.status = 'accepted'
    workgroup_member.save()

    notification.read = True
    notification.save()

    Notification.objects.create(
        recipient=workgroup_member.user,
        sender=request.user,
        workgroup=workgroup_member.workgroup,
        title=f'Your request to join {workgroup_member.workgroup.name} has been accepted',
        body=f'{request.user.username} has accepted your request to join the workgroup "{workgroup_member.workgroup.name}".',
        read=False,
        type='invitation'
    )


    return JsonResponse({'status': 'success', 'message': 'Join request accepted successfully.'})


@login_required
def deny_join(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    if not notification.workgroup:
        return JsonResponse({'status': 'error', 'message': 'Invalid notification.'})

    workgroup_member = WorkGroupMember.objects.filter(
        user=notification.sender,
        workgroup=notification.workgroup
    ).first()

    if not workgroup_member or request.user != workgroup_member.workgroup.creator:
        return HttpResponseForbidden("You are not authorized to deny this join request.")

    workgroup_member.status = 'denied'
    workgroup_member.save()

    Notification.objects.create(
        recipient=workgroup_member.user,
        sender=request.user,
        workgroup=workgroup_member.workgroup,
        title=f'Your request to join {workgroup_member.workgroup.name} has been denied',
        body=f'{request.user.username} has denied your request to join the workgroup "{workgroup_member.workgroup.name}".',
        read=False,
        type='invitation'
    )


    return JsonResponse({'status': 'success', 'message': 'Join request denied successfully.'})



@login_required
def accept_invitation(request, pk):
    try:
        member = WorkGroupMember.objects.get(workgroup_id=pk, user=request.user, status='pending')
        member.status = 'accepted'
        member.save()
        # Rediriger vers la page du groupe de travail ou une autre page appropriée
        return HttpResponseRedirect(reverse('workgroup_detail', args=[pk]))
    except WorkGroupMember.DoesNotExist:
        # Gérer le cas où l'invitation n'existe pas ou a déjà été traitée
        return HttpResponseForbidden("Invalid request or invitation already handled.")

@login_required
def refuse_invitation(request, pk):
    try:
        member = WorkGroupMember.objects.get(workgroup_id=pk, user=request.user, status='pending')
        member.status = 'refused'
        member.save()
        # Rediriger vers une page appropriée
        return HttpResponseRedirect(reverse('home'))
    except WorkGroupMember.DoesNotExist:
        # Gérer le cas où l'invitation n'existe pas ou a déjà été traitée
        return HttpResponseForbidden("Invalid request or invitation already handled.")

@login_required
def create_chat_room(request, workgroup_id):
    # Récupérer le workgroup
    workgroup = get_object_or_404(WorkGroup, pk=workgroup_id, creator=request.user)

    # Créer la chat room
    ChatRoom.objects.create(workgroup=workgroup)

    # Parcourir tous les membres du workgroup ayant le statut 'accepted'
    members = WorkGroupMember.objects.filter(workgroup=workgroup, status='accepted')
    for member in members:
        # Ne pas notifier le créateur de la chat room
        if member.user != request.user:
            Notification.objects.create(
                recipient=member.user,
                workgroup=workgroup,
                title=f'New Chat Room in {workgroup.name}',
                body=f'A new chat room has been created in the workgroup "{workgroup.name}".',
                read=False,
                type='room_launched'
            )

    # Rediriger vers la page de détail du workgroup
    return redirect('workgroup_detail', pk=workgroup_id)


@login_required
def chat_room(request, chat_room_id):
    chat_room = get_object_or_404(ChatRoom, pk=chat_room_id)
    workgroup = chat_room.workgroup  # Accès au WorkGroup associé

    workgroup_id = workgroup.id  # Récupération de l'ID du WorkGroup
    # Récupérer le premier assistant associé au WorkGroup, si disponible
    assistant = workgroup.assistants.first() if workgroup.assistants.exists() else None
    assistant_user = None
    User = get_user_model()
    if workgroup.with_assistant:
        assistant_user, _ = User.objects.get_or_create(username=assistant.name)

    # Vérifier si l'utilisateur est membre du groupe de travail
    if not workgroup.members.filter(id=request.user.id).exists() and request.user != workgroup.creator:
        return HttpResponseForbidden("You do not have permission to access this chat room.")

    online_status, created = UserOnlineStatus.objects.get_or_create(user=request.user)
    online_status.set_online()

    members = workgroup.members.all()
    return render(request, 'workgroup/discussion_room.html', {'chat_room': chat_room, 'members': members, 'workgroup_id': workgroup_id,'assistant': assistant, 'assistant_user':assistant_user})


@login_required
def join_workgroup(request, workgroup_id):
    if request.method == 'POST':
        workgroup = get_object_or_404(WorkGroup, pk=workgroup_id)

        existing_member = WorkGroupMember.objects.filter(user=request.user, workgroup=workgroup)

        if existing_member.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'You have already requested to join or are a member of this workgroup.'
            })

        WorkGroupMember.objects.create(
            user=request.user,
            workgroup=workgroup,
            status='pending'
        )

        Notification.objects.create(
            recipient=workgroup.creator,
            sender=request.user,  # Ajoutez le sender ici
            workgroup=workgroup,
            title=f'Join Request from {request.user.username}',
            body=f'{request.user.username} has requested to join your workgroup "{workgroup.name}".',
            type='join_request',
            read=False
        )

        return JsonResponse({'status': 'success', 'message': 'Join request sent successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

from openai import OpenAI
import os
import datetime
import time


client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))
@require_http_methods(["POST"])
def assistant_endpoint(request, workgroup_id):

    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        user_message = data.get('message')

        # Récupérez l'assistant depuis la base de données en utilisant le nom
        try:
            assistant_name = None
            if workgroup_id:
                workgroup = WorkGroup.objects.get(id=workgroup_id)
                # Supposons que vous vouliez récupérer le premier assistant
                assistant = workgroup.assistants.first()
                if assistant:
                    assistant_name = assistant.name
            #print(assistant_name,user_message)
            assistant = OpenAIAssistant.objects.get(name=assistant_name)
        except OpenAIAssistant.DoesNotExist:
            return JsonResponse({'error': 'Assistant not found'}, status=404)

        file_id = assistant.file_id
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
                else:
                    print("Waiting for the Assistant to process...")
                    time.sleep(5)

            # Trouver le dernier message de l'assistant
            last_assistant_message_content = None
            for message in reversed(serializable_messages):
                if message['role'] == 'assistant':
                    last_assistant_message_content = message['content']
                    break

            # Vérifier si un message de l'assistant a été trouvé
            if last_assistant_message_content:
                return JsonResponse({'response': last_assistant_message_content})
            else:
                # Gérer le cas où aucun message de l'assistant n'est trouvé
                return JsonResponse({'error': 'No assistant message found'}, status=404)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
