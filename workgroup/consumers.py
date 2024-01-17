# your_app/consumers.py
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.templatetags.static import static

from workgroup.models import WorkGroup, MessageAudio

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Connectez-vous au groupe de notification spécifique à l'utilisateur
        self.group_name = f'notifications_{self.scope["user"].id}'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Quittez le groupe à la déconnexion
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive_notification(self, event):
        # Recevoir une notification depuis le backend
        notification = event['notification']
        await self.send(text_data=json.dumps(notification))

logger = logging.getLogger('workgroup')
User = get_user_model()
class ChatConsumer(AsyncWebsocketConsumer):

    @database_sync_to_async
    def set_user_online(self, user):
        user.online_status.set_online()

    @database_sync_to_async
    def set_user_offline(self, user):
        user.online_status.set_offline()
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['workgroup_id']
        self.room_group_name = f'chat_{self.room_name}'
        # logger.debug(f"Attempting to connect to room: {self.room_name}")

        # Rejoindre la room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Ajouter l'utilisateur à la liste des utilisateurs connectés
        await self.add_user_to_list(self.scope["user"])
        # Envoyer la liste des utilisateurs connectés à tous les utilisateurs dans la salle
        await self.send_user_list_to_group()
        await self.set_user_online(self.scope["user"])

    async def disconnect(self, close_code):
        # Quitter la room
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        # Supprimer l'utilisateur de la liste des utilisateurs connectés
        # await self.remove_user_from_list(self.scope["user"])
        # Envoyer la liste des utilisateurs connectés mise à jour à tous les utilisateurs dans la salle
        await self.send_user_list_to_group()
        await self.set_user_offline(self.scope["user"])

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        if bytes_data:
            # Traiter les données audio
            workgroup_id = self.room_name
            workgroup = await self.get_workgroup(workgroup_id)
            audio_message = await self.save_audio_message(user, workgroup, bytes_data)
            await self.send_audio_message_to_group(audio_message)
        elif text_data:
            text_data_json = json.loads(text_data)

            # Vérifiez si la clé 'message' est présente dans le message reçu
            message = text_data_json.get('message')
            if message is None:
                #logger.error("Aucun message reçu dans le message WebSocket")
                return  # Vous pouvez choisir de ne rien faire ou de gérer cette situation différemment


            username = user.username
            user_id = user.id
            avatar_url = await self.get_avatar_url(user)
            message_type = text_data_json.get('type')

            if message_type == "call_started":
                await self.broadcast_call_started()

            if message_type in ["store_offer", "store_candidate", "store_user"]:
                # Gérer les messages WebRTC
                await self.handle_webrtc_message(text_data_json, user)

            # Envoi du message au groupe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username,
                    'user_id': user_id,
                    'avatar_url': avatar_url,
                }
            )

    async def handle_webrtc_message(self, message, user):
        # Votre logique pour gérer les messages WebRTC
        # Par exemple, transmettre l'offre, la réponse, et les candidats ICE aux autres utilisateurs
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_signal',
                'message': message
            }
        )

    async def broadcast_call_started(self):
        # Envoyer un message à tous les utilisateurs dans la room indiquant que l'appel a commencé
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.call_started',  # Modifiez le 'type' ici pour qu'il corresponde à une méthode de gestion dans votre consommateur
            }
        )

    async def chat_call_started(self, event):
        # Envoyer le message à WebSocket
        await self.send(text_data=json.dumps({
            'type': 'call_started'
        }))


    async def signal_call_started(self, event):
        # Envoyer le message à WebSocket
        await self.send(text_data=json.dumps({'type': 'call_started'}))

    async def handle_webrtc_message(self, message, user):
        # Gérer les messages WebRTC
        # Par exemple, transmettre l'offre, la réponse, et les candidats ICE aux autres utilisateurs
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'webrtc_signal',
                'message': message
            }
        )

    async def webrtc_signal(self, event):
        # Envoyer le message WebRTC au WebSocket
        await self.send(text_data=json.dumps(event['message']))

    # Dans votre méthode de consommateur
    @database_sync_to_async
    def get_avatar_url(self, user):
        avatar_url = user.profile.avatar.url if user.profile.avatar else static('images/pp.svg')
        #logger.debug(f"Avatar URL: {avatar_url}")
        return avatar_url

    async def chat_message(self, event):
        # Envoi du message au WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'avatar_url': event['avatar_url'],
        }))

    @database_sync_to_async
    def add_user_to_list(self, user):
        try:
            workgroup_id = int(self.room_name)
            workgroup = WorkGroup.objects.get(id=workgroup_id)
        except (ValueError, WorkGroup.DoesNotExist):
            # Gérer l'erreur si l'ID n'est pas un nombre ou si le WorkGroup n'existe pas
            logger.error(f"WorkGroup with id {workgroup_id} does not exist.")
            return []

        workgroup.members.add(user)
        return workgroup.members.all()

    @database_sync_to_async
    def remove_user_from_list(self, user):
        workgroup_id = self.room_name # Assurez-vous que cela correspond à la structure de vos URL
        workgroup = WorkGroup.objects.get(id=workgroup_id)
        workgroup.members.remove(user)
        return workgroup.members.all()


    async def send_user_list_to_group(self):
        # Cette méthode devrait être appelée après chaque connexion ou déconnexion
        users = await self.get_users()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.user_list',
                'users': users
            }
        )

    @database_sync_to_async
    def get_users(self):
        # Récupérer la liste des utilisateurs dans le groupe/room
        workgroup_id = self.room_name
        workgroup = WorkGroup.objects.get(id=workgroup_id)
        user_list = []
        for user in workgroup.members.all():
            try:
                online_status = user.online_status.is_online
            except User.online_status.RelatedObjectDoesNotExist:
                online_status = False
            user_list.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else static('images/pp.svg'),
                'is_online': online_status
            })
        return user_list


    # Gérer le message de type 'user_list' envoyé à tous les clients
    async def chat_user_list(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_list',
            'users': event['users']
        }))
    @database_sync_to_async
    def save_audio_message(self, user, workgroup, audio_data):
        audio_message = MessageAudio.objects.create(
            workgroup=workgroup,
            user=user,
            audio_file=ContentFile(audio_data, name="audio_message.wav")  # Nommer le fichier audio
        )
        return audio_message

    @database_sync_to_async
    def get_workgroup(self, workgroup_id):
        return WorkGroup.objects.get(id=workgroup_id)

    async def send_audio_message_to_group(self, audio_message):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.audio_message',
                'audio_url': audio_message.audio_file.url,
                'username': audio_message.user.username,
                'user_id': audio_message.user.id
            }
        )

    async def chat_audio_message(self, event):
        # L'URL de l'audio et les autres détails sont déjà inclus dans l'événement
        audio_url = event['audio_url']
        username = event['username']
        user_id = event['user_id']

        # Envoyer ces détails au client via WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat.audio_message',
            'audio_url': audio_url,
            'username': username,
            'user_id': user_id
        }))


# class CallConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope['url_route']['kwargs'].get('room_name', 'default_room')
#         self.room_group_name = 'call_%s' % self.room_name
#
#         # Rejoindre la room
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#
#         await self.accept()
#
#     async def disconnect(self, close_code):
#         # Quitter la room
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
#
#     # Recevoir des messages de WebSocket
#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message_type = text_data_json['type']
#
#         if message_type == "store_user":
#             # Gérer la logique de stockage de l'utilisateur ici
#             pass
#         elif message_type == "store_offer":
#             # Gérer la logique de l'offre WebRTC ici
#             pass
#         elif message_type == "store_candidate":
#             # Gérer la logique des candidats ICE ici
#             pass
#         elif message_type == "call_started":
#             await self.broadcast_call_started()
#
#         # Envoyer le message aux autres utilisateurs de la room
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'signal_message',
#                 'message': text_data_json
#             }
#         )
#
#     # Recevoir des messages du groupe
#     async def signal_message(self, event):
#         message = event['message']
#
#         # Envoyer le message à WebSocket
#         await self.send(text_data=json.dumps(message))
#
#     async def broadcast_call_started(self):
#         # Envoyer un message à tous les utilisateurs dans la room indiquant que l'appel a commencé
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'signal_call_started',
#             }
#         )
#
#     async def signal_call_started(self, event):
#         # Envoyer le message à WebSocket
#         await self.send(text_data=json.dumps({'type': 'call_started'}))
