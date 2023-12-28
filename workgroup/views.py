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
        'read': notification.read  # Ajoutez l'état de lecture
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
            status='invited'
        )

        Notification.objects.create(
            recipient=user,
            workgroup=workgroup,  # Ajout de l'instance WorkGroup à la notification
            title=f'Invitation to join {workgroup.name}',
            body=f'You have been invited to join the workgroup "{workgroup.name}" by {request.user.username}',
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
        is_allowed = member.status in ['invited', 'accepted']
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
def create_workgroup(request):
    with_assistant = False
    if request.method == 'POST':
        form = RevisionForm(request.POST, request.FILES)
        if form.is_valid():
            workgroup = form.save(commit=False)
            workgroup.creator = request.user
            workgroup.save()
            form.save_m2m()

            # Associer OpenAIAssistant si demandé
            if 'create_with_assistant' in request.POST:
                assistant = OpenAIAssistant.objects.first() # Ou une logique pour sélectionner un assistant spécifique
                workgroup.assistants.add(assistant) # Supposant un champ ManyToManyField pour assistants
                with_assistant = True

            return redirect('workgroup_detail', pk=workgroup.pk)
    else:
        form = RevisionForm()

    return render(request, 'workgroup/create_workgroup.html', {'form': form, 'with_assistant': with_assistant})


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
def accept_invitation(request, pk):
    try:
        member = WorkGroupMember.objects.get(workgroup_id=pk, user=request.user, status='invited')
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
        member = WorkGroupMember.objects.get(workgroup_id=pk, user=request.user, status='invited')
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
    # Vérifiez si l'utilisateur a le droit de voir ce salon de discussion
    # Mettez à jour l'état en ligne de l'utilisateur
    online_status, created = UserOnlineStatus.objects.get_or_create(user=request.user)
    online_status.set_online()

    # Récupérer les messages, etc.
    return render(request, 'workgroup/discussion_room.html', {'chat_room': chat_room})

