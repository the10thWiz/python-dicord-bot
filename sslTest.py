import http.client as client
import json
import time
import ssl
import socket
import websocket as ws

def log(message):
	print('['+time.strftime('%H:%M:%S')+'] ', message)

with open('secret.json') as secret_json:
    secret = json.load(secret_json)


# c = client.HTTPSConnection('discordapp.com')
# c.request('GET', '/api/v6/guilds/502224796109635586', headers={
# 	'Authorization':'Bot '+secret.get('token'),
# 	'User-Agent': 'DiscordBot ('+secret.get('url')+', '+secret.get('version')+')'
# })

# response = c.getresponse()
# print(response.status, response.reason)
# data = response.read()

def makeRequest(method, path, params=[], body=''):
    c = client.HTTPSConnection('discordapp.com')
    req = '/api/v6'
    for s in path:
        req += '/' + s
    c.request(method, req, headers={
        'Authorization': 'Bot '+secret.get('token'),
        'User-Agent': 'DiscordBot ('+secret.get('url')+', '+secret.get('version')+')'
    })

    response = c.getresponse()

    return json.load(response)

def createPayload(opCode, data):
	return {
		'op': opCode,
		'd': data
	}

guilds = []
seq = None
heartbeatInv = 1000000000
receivedACK = False
nextBeat = time.time() + heartbeatInv

def handleEvent(type, data):
	if type == "GUILD_CREATE":
		guilds.append(data)
	else:
		log(type)
	return

def listen():
	url = makeRequest('GET', ['gateway']).get('url')+"?v=6&encoding=json"
	sock = ws.create_connection(url)
	sock.settimeout(2)
	while sock.connected:
		# log(sock.getstatus())
		try:
			raw = sock.recv()
		except (TimeoutError, ws._exceptions.WebSocketTimeoutException):
			raw = ''
		except ws._exceptions.WebSocketConnectionClosedException as e:
			log(e)
			return
		if raw != '':
			data = json.loads(raw)
			opCode = data.get('op')
			if opCode == 0:
				# handle event
				handleEvent(data.get('t'), data.get('d'))
			elif opCode == 1:
				# handle ping
				log('Pinged')
				pass
			elif opCode == 10:
				# hello
				heartbeatInv = (data.get('d').get('heartbeat_interval')-10)/1000
				log(heartbeatInv)
				nextBeat = time.time() + heartbeatInv
				receivedACK = True
				sock.send(json.dumps(createPayload(2, secret.get('identity'))))
			elif opCode == 11:
				# hello
				receivedACK = True
				log('Recieved ACK')
				pass
			else:
				log(opCode)
		else:
			log('No Packets '+str(nextBeat - time.time()))
			if time.time() >= nextBeat:
				log('HeartBeat')
				if not receivedACK:
					log("Connection lost")
				sock.send(json.dumps(createPayload(2, seq)))
				receivedACK = False
				nextBeat = time.time() + heartbeatInv
		sock.settimeout(nextBeat - time.time())
		log(sock.gettimeout())
			



# print(makeRequest('GET', ['guilds', '502224796109635586', 'channels'])[1].get('name'))
listen()