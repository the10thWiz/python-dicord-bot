import aiohttp
import aiofile
import json
import time
import asyncio
import websockets
import logging
import sys

def fake(json):
    pass

class httpAPI:
    """ Class for http reqs """
    def __init__(self, secret, loop, logger, url = 'https://discordapp.com/api/v6'):
        self.session = aiohttp.ClientSession(headers={
            'Authorization': 'Bot '+secret['token'],
            'User-Agent': 'DiscordBot ('+secret['url']+', '+secret['version']+')',
            'Content-Type': 'application/json'
        })
        self.url = url
        self.loop = loop
        self.logger = logger
    async def makeAioRequest(self, method, path, params=None, body=None, consumer=fake):
        url = self.url
        for s in path:
            url += f'/{s}'
        self.logger.info(f'Sending https request {method} {url}')
        async with self.session.request(method, url, params=params, json=body) as res:
            try:
                res_json = await res.json()
                self.logger.info(f'Https reply {res_json}')
                consumer(res_json)
                return res_json
            except:
                consumer({})
                return {}
    # convience function to synchronously start an asynchronous makeAioRequest
    def sendMessage(self, method, path, params=None, body=None, consumer=fake):
        try:
            asyncio.create_task(self.makeAioRequest(method, path, params=params, body=body, consumer=consumer))
        except:
            self.loop.create_task(self.makeAioRequest(method, path, params=params, body=body, consumer=consumer))
    def message(self, ch, content):
        self.sendMessage('POST', ['channels', ch, 'messages'], body={'content': content})
    def react(self, ch, mes, emoji):
        self.sendMessage('POST', ['channels', ch, 'messages', mes, 'reactions', emoji, '@me'])
    def emoji(self, guild, consumer):
        self.sendMessage('GET', ['guilds', guild, 'emojis'], consumer=consumer)

class discordBot:
    """ Class to interact with the code Discord API """
    def __init__(self, loadFromState = True, secretFile = 'secret.json', stateFile = 'state.json'):
        self.secret = {}
        self.stateFile = stateFile
        self.state = {
            'time': '',
            'sessionId': '',
            'seq': None,
        }
        self.guilds = {}
        self.loop = asyncio.get_event_loop()
        self.__configLog__()
        self.loop.run_until_complete(self.__loadAPI__(secretFile))
        if loadFromState:
           pass
        self.onChannelCreate = self.__fakeEventHandler__ #new channel created
        self.onChannelUpdate = self.__fakeEventHandler__ #channel was updated
        self.onChannelDelete = self.__fakeEventHandler__ #channel was deleted
        self.onChannelPinsUpdate = self.__fakeEventHandler__ #message was pinned or unpinned
        self.onGuildCreate = self.__fakeEventHandler__ #lazy-load for unavailable guild, guild became available, or user joined a new guild
        self.onGuildUpdate = self.__fakeEventHandler__ #guild was updated
        self.onGuildDelete = self.__fakeEventHandler__ #guild became unavailable, or user left/was removed from a guild
        self.onGuildBanAdd = self.__fakeEventHandler__ #user was banned from a guild
        self.onGuildBanRemove = self.__fakeEventHandler__ #user was unbanned from a guild
        self.onGuildEmojisUpdate = self.__fakeEventHandler__ #guild emojis were updated
        self.onGuildIntegrations = self.__fakeEventHandler__ #Update	guild integration was updated
        self.onGuildMemberAdd = self.__fakeEventHandler__ #new user joined a guild
        self.onGuildMemberRemove = self.__fakeEventHandler__ #user was removed from a guild
        self.onGuildMemberUpdate = self.__fakeEventHandler__ #guild member was updated
        self.onGuildMembersChunk = self.__fakeEventHandler__ #response to Request Guild Members
        self.onGuildRoleCreate = self.__fakeEventHandler__ #guild role was created
        self.onGuildRoleUpdate = self.__fakeEventHandler__ #guild role was updated
        self.onGuildRoleDelete = self.__fakeEventHandler__ #guild role was deleted
        self.onMessageCreate = self.__fakeEventHandler__ #message was created
        self.onMessageUpdate = self.__fakeEventHandler__ #message was edited
        self.onMessageDelete = self.__fakeEventHandler__ #message was deleted
        self.onMessageDeleteBulk = self.__fakeEventHandler__ #Bulk	multiple messages were deleted at once
        self.onMessageReactionAdd = self.__fakeEventHandler__ #Add	user reacted to a message
        self.onMessageReactionRemove = self.__fakeEventHandler__ #Remove	user removed a reaction from a message
        self.onMessageReactionRemoveAll = self.__fakeEventHandler__ #Remove All	all reactions were explicitly removed from a message
        self.onPresenceUpdate = self.__fakeEventHandler__ #user was updated
        self.onTypingStart = self.__fakeEventHandler__ #user started typing in a channel
        self.onUserUpdate = self.__fakeEventHandler__ #properties about the user changed
        self.onVoiceStateUpdate = self.__fakeEventHandler__ #	someone joined, left, or moved a voice channel
        self.onVoiceServerUpdate = self.__fakeEventHandler__ # guild's voice server was updated
        self.onWebhooksUpdate = self.__fakeEventHandler__ #guild channel webhook was created, update, or deleted
    def __fakeEventHandler__(self, event):
        pass
    """ Config logger with params """
    def __configLog__(self):
        self.logger = logging.getLogger('bot')
    """ writes state to stateFile """
    async def __writeState__(self):
        async with aiofile.AIOFile(self.stateFile, 'w') as s:
            self.state['time'] = time.time()
            await s.write(json.dumps(self.state))
    """ connects to http s api """
    async def __loadAPI__(self, secretFile):
        async with aiofile.AIOFile(secretFile) as secret_json:
            self.secret = json.loads(await secret_json.read())
        self.http = httpAPI(self.secret, self.loop, self.logger)
    async def __heartbeat__(self, ws, heartbeatInterval):
        while True:
            await asyncio.sleep(heartbeatInterval)
            self.logger.info(f'Heartbeat seq: {self.state["seq"]}')
            if not self.receivedACK:
                self.logger.warning('Connection Lost: No ACK')
            await self.__sendPayload__(1, self.state['seq'])
            self.receivedACK = False
    async def __identify__(self, data):
        heartbeatInv = (data['heartbeat_interval'] - 10)/1000
        self.logger.info(f'Heartbeat Interval: {heartbeatInv}')
        # send identity payload (op 2, payload is in secret.json)
        # TODO add resume option
        await self.__sendPayload__(2, self.secret['identity'])
        # start heartbeat task AFTER identifing
        asyncio.create_task(self.__heartbeat__(self.ws, heartbeatInv))
    async def __sendPayload__(self, opCode, data):
        await self.ws.send(json.dumps({
            'op': opCode,
            'd': data
        }))
    async def __guildEvent__(self, type, data):
        # global send
        if type == 'READY':
            self.logger.info(f'Ready, Version: {data["v"]}')
            self.state['sessionId'] = data['session_id']
        elif type == 'GUILD_CREATE':
            self.logger.info(f'Added Guild: {data["name"]}')
            self.guilds[data['id']] = data
            self.onGuildCreate({
                'bot':self,
                'event':type,
                'guild':data['id'],
                'data':data
            })
        elif type == 'GUILD_UPDATE':
            self.guilds[data['id']] = {self.guilds[data['id']], data}
            self.onGuildUpdate({
                'bot':self,
                'event':type,
                'guild':data['id'],
                'data':data
            })
        elif type == 'GUILD_DELETE':
            self.guilds.pop(data['id'], None)
            self.onGuildDelete({
                'bot':self,
                'event':type,
                'guild':data['id'],
                'data':data
            })
        elif type == 'CHANNEL_CREATE':
            self.onChannelCreate({
                'bot':self,
                'event':type,
                'channel':data['id'],
                'data':data,
            })
        elif type == 'CHANNEL_UPDATE':
            self.onChannelUpdate({
                'bot':self,
                'event':type,
                'channel':data['id'],
                'data':data,
            })
        elif type == 'CHANNEL_DELETE':
            self.onChannelDelete({
                'bot':self,
                'event':type,
                'channel':data['id'],
                'data':data,
            })
        elif type == 'CHANNEL_PINS_UPDATE':
            self.onChannelPinsUpdate({
                'bot':self,
                'event':type,
                'channel':data['id'],
                'data':data,
            })
        elif type == 'GUILD_BAN_ADD':
            self.onGuildBanAdd({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'user':data['user'],
                'data':data
            })
        elif type == 'GUILD_BAN_REMOVE':
            self.onGuildBanRemove({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'user':data['user'],
                'data':data,
            })
        elif type == 'GUILD_EMOJIS_UPDATE':
            self.onGuildEmojisUpdate({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'emojis':data['emojis'],
                'data':data,
            })
        elif type == 'GUILD_INTEGRATIONS':
            self.onGuildIntegrations({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'data':data,
            })
        elif type == 'GUILD_MEMBER_ADD':
            self.onGuildMemberAdd({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'user':data['user'],
                'data':data,
            })
        elif type == 'GUILD_MEMBER_REMOVE':
            self.onGuildMemberRemove({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'user':data['user'],
                'data':data,
            })
        elif type == 'GUILD_MEMBER_UPDATE':
            self.onGuildMemberUpdate({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'user':data['user'],
                'data':data,
            })
        elif type == 'GUILD_MEMBERS_CHUNK':
            self.onGuildMembersChunk({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'users':data['members'],
                'data':data,
            })
        elif type == 'GUILD_ROLE_CREATE':
            self.onGuildRoleCreate({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'role':data['role'],
                'data':data,
            })
        elif type == 'GUILD_ROLE_UPDATE':
            self.onGuildRoleUpdate({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'role':data['role'],
                'data':data,
            })
        elif type == 'GUILD_ROLE_DELETE':
            self.onGuildRoleDelete({
                'bot':self,
                'event':type,
                'guild':data['guild_id'],
                'role':data['role'],
                'data':data,
            })
        elif type == 'MESSAGE_CREATE':
            self.logger.info(f'Message Recieved: {data["content"]}')
            try :
                if not data['author']['bot']:
                    self.onMessageCreate({
                        'bot':self,
                        'event':type,
                        'id':data['id'],
                        'channel':data['channel_id'],
                        'user':data['author'],
                        'content':data['content'],
                        'data':data,
                    })
            except:
                self.onMessageCreate({
                    'bot':self,
                    'event':type,
                    'id':data['id'],
                    'channel':data['channel_id'],
                    'user':data['author'],
                    'content':data['content'],
                    'data':data,
                })
        elif type == 'MESSAGE_UPDATE':
            self.onMessageUpdate({
                'bot':self,
                'event':type,
                'id':data['id'],
                'channel':data['channel_id'],
                'user':data['author'],
                'content':data['content'],
                'data':data,
            })
        elif type == 'MESSAGE_DELETE':
            self.onMessageDelete({
                'bot':self,
                'event':type,
                'id':data['id'],
                'channel':data['channel_id'],
                'data':data,
            })
        elif type == 'MESSAGE_DELETE_BULK':
            self.onMessageDeleteBulk({
                'bot':self,
                'event':type,
                'id':data['id'],
                'channel':data['channel_id'],
                'data':data,
            })
        elif type == 'MESSAGE_REACTION_ADD':
            self.onMessageReactionAdd({
                'bot':self,
                'event':type,
                'channel':data['channel_id'],
                'message':data['message_id'],
                'emoji':data['emoji'],
                'data':data,
            })
        elif type == 'MESSAGE_REACTION_REMOVE':
            self.onMessageReactionRemove({
                'bot':self,
                'event':type,
                'channel':data['channel_id'],
                'message':data['message_id'],
                'emoji':data['emoji'],
                'data':data,
            })
        elif type == 'MESSAGE_REACTION_REMOVE_ALL':
            self.onMessageReactionRemoveAll({
                'bot':self,
                'event':type,
                'channel':data['channel_id'],
                'message':data['message_id'],
                'data':data,
            })
        elif type == 'PRESENCE_UPDATE':
            self.onPresenceUpdate({
                'bot':self,
                'event':type,
                'user':data['user'],
                'game':data['game'],
                'status':data['status'],
                'data':data,
            })
        elif type == 'TYPING_START':
            self.onTypingStart({
                'bot':self,
                'event':type,
                'user':data['user_id'],
                'channel':data['channel_id'],
                'data':data,
            })
        elif type == 'USER_UPDATE':
            self.onUserUpdate({
                'bot':self,
                'event':type,
                'user':data['user'],
                'data':data,
            })
        elif type == 'VOICE_STATE_UPDATE':
            self.onVoiceStateUpdate({
                'bot':self,
                'event':type,
                'user':data['user_id'],
                'data':data,
            })
        elif type == 'VOICE_SERVER_UPDATE':
            self.onVoiceServerUpdate({
                'bot':self,
                'event':type,
                'data':data,
            })
        elif type == 'WEBHOOK_UPDATE':
            self.onWebhooksUpdate({
                'bot':self,
                'event':type,
                'data':data,
            })
        else:
            self.logger.debug(f'Unknown type: {type}')
        asyncio.create_task(self.__writeState__())
    async def __handleEvent__(self, opCode, data):
        if opCode == 0:
            # update sequence number
            self.state['seq'] = data['s']
            await self.__guildEvent__(data['t'], data['d'])
        elif opCode == 1:
            self.logger.info('Pinged')
        elif opCode == 7:
            self.logger.warning('Reconnect')
            return
        elif opCode == 9:
            self.logger.warning('Invalid Session')
            return
        elif opCode == 10:
            # to avoid false connection lost b/c we haven't recieved an ACK before sending a heartbeat
            self.receivedACK = True
            await self.__identify__(data['d'])
        elif opCode == 11:
            self.receivedACK = True
            self.logger.info('Recieved ACK')
            pass
        else:
            self.logger.warning(f'Unknown opCode: {opCode}')
    async def __main__(self):
        self.logger.debug('Bot starting')
        async with websockets.connect((await self.http.makeAioRequest('GET', ['gateway']))['url']+'?v=6&encoding=json') as ws:
            self.ws = ws
            while True:
                try:
                    raw = await ws.recv()
                except Exception as e:
                    self.logger.warning(f'Exception while reading: {e}')
                    if ws.closed:
                        self.ws = None
                        return
                    raw = ''
                if raw != '':
                    # convert raw json to data, and grab opCode to handle event
                    data = json.loads(raw)
                    opCode = data['op']
                    await self.__handleEvent__(opCode, data)
                else:
                    self.logger.warning('No Packets')
    def runBot(self):
        self.loop.run_until_complete(self.__main__())
    
