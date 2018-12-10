import logging
import random
from discord import discordBot as dBot

logging.basicConfig(filename='pyBot.log', filemode='w', level=logging.DEBUG,
                    format='%(levelname)s:%(name)s:%(asctime)s:%(message)s')
wslogger = logging.getLogger('websockets')
wslogger.setLevel(logging.INFO)
wslogger.addHandler(logging.StreamHandler())

logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

def sendStat(bot, ch):
    bot.http.message(ch, 'I\'m Alive!')

def onMessage(event):
    command = event['content'].split(' ')
    if not command[0][0] == '&':
        return
    if command[0] == '&stat':
        sendStat(event['bot'], event['channel'])

uuidValues = [chr(i) for i in range(ord('a'), ord('z')+1)]+[ chr(i) for i in range(ord('A'), ord('Z')+1)]+[ chr(i) for i in range(ord('0'), ord('9')+1)]
def uuidGen(prefix):
    uuid = ''
    while len(uuid) < 16:
        uuid+= uuidValues[random.randrange(0, len(uuidValues))]
    return prefix+'_'+uuid

collectableData = {}

print(uuidGen('C'))

# bot = dBot()

# bot.onMessageCreate = onMessage

# bot.runBot()