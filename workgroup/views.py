import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from mentoring_app.models import Notification
from smart_mentor.models import Profile, OpenAIAssistant
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
        user_profiles = Profile.objects.filter(user__username__icontains=query)
        assistants = OpenAIAssistant.objects.filter(name__icontains=query)

        # Créez une liste combinée de profils et d'assistants
        results = [
                      {'type': 'profile', 'username': profile.user.username, 'avatar': profile.avatar.url if profile.avatar else None}
                      for profile in user_profiles
                  ] + [
                      {'type': 'assistant', 'name': assistant.name, 'description': assistant.description}
                      for assistant in assistants
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
        'type': notification.type
    } for notification in notifications]

    unread_count = notifications.filter(read=False).count()  # Compter uniquement les notifications non lues

    return JsonResponse({'notifications': notifications_data, 'unread_count': unread_count})

@login_required
@require_POST
def send_invitation(request):
    try:
        data = json.loads(request.body)
        username = data['username']
        user = User.objects.get(username=username)
        workgroup_id = data['workgroup_id']  # Assurez-vous de passer l'ID du groupe de travail
        workgroup = WorkGroup.objects.get(id=workgroup_id)

        # Créer une instance WorkGroupMember avec le statut 'invited'
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

def workgroup_detail(request, pk):
    workgroup = get_object_or_404(WorkGroup, pk=pk)

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

    members_info = WorkGroupMember.objects.filter(workgroup=workgroup).select_related('user')
    chat_rooms = workgroup.chatrooms.all()
    return render(request, 'workgroup/classroom.html', {
        'workgroup': workgroup,
        'members_info': members_info,
        'is_creator': workgroup.creator == request.user,
        'is_accepted': is_accepted,
        'chat_rooms': chat_rooms,
    })

@login_required
@require_POST
def clear_all_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    return JsonResponse({'status': 'success', 'message': 'All notifications cleared.'})
@login_required
def create_workgroup(request):
    # Créer un utilisateur pour l'assistant
    assistant_user, created = User.objects.get_or_create(
        username='assistant',  # Un identifiant unique
        defaults={
            'first_name': 'OpenAI',
            'last_name': 'Assistant',
            # Autres champs nécessaires
        }
    )

    if created or not hasattr(assistant_user, 'profile'):
        # Si l'utilisateur assistant est nouvellement créé ou n'a pas de profil
        profile, profile_created = Profile.objects.get_or_create(
            user=assistant_user,
            defaults={'avatar': 'avatars_workgroup/assistant_avatar.png'}
        )
        if not profile_created:
            # Si le profil existait déjà, mais doit être mis à jour
            profile.avatar = 'avatars_workgroup/assistant_avatar.png'
            profile.save()

    if request.method == 'POST':
        form = RevisionForm(request.POST, request.FILES)
        if form.is_valid():
            workgroup = form.save(commit=False)
            workgroup.creator = request.user
            workgroup.with_assistant = 'create_with_assistant' in request.POST
            workgroup.save()
            form.save_m2m()

            # Vérifier si l'assistant doit être ajouté
            if  workgroup.with_assistant :
                # Récupérer l'utilisateur assistant
                assistant_user = User.objects.get(username='assistant')

                # Ajouter l'assistant en tant que membre du groupe
                WorkGroupMember.objects.create(
                    user=assistant_user,
                    workgroup=workgroup,
                    status='accepted'  # ou 'pending', selon la logique de votre application
                )

            return redirect('workgroup_detail', pk=workgroup.pk)

    else:
        form = RevisionForm()

    return render(request, 'workgroup/create_workgroup.html', {'form': form,'assistant': assistant_user})



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
    workgroup = get_object_or_404(WorkGroup, pk=workgroup_id, creator=request.user)
    ChatRoom.objects.create(workgroup=workgroup)
    return redirect('workgroup_detail', pk=workgroup_id)

@login_required
def chat_room(request, chat_room_id):
    chat_room = get_object_or_404(ChatRoom, pk=chat_room_id)
    workgroup = chat_room.workgroup  # Accès au WorkGroup associé

    workgroup_id = workgroup.id  # Récupération de l'ID du WorkGroup

    # Vérifier si l'utilisateur est membre du groupe de travail
    if not workgroup.members.filter(id=request.user.id).exists() and request.user != workgroup.creator:
        return HttpResponseForbidden("You do not have permission to access this chat room.")

    online_status, created = UserOnlineStatus.objects.get_or_create(user=request.user)
    online_status.set_online()

    members = workgroup.members.all()
    return render(request, 'workgroup/discussion_room.html', {'chat_room': chat_room, 'members': members, 'workgroup_id': workgroup_id})

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


