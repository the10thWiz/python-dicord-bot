import logging
import subprocess as sp
import json
import shlex
import threading

execFile = '/home/matthew/Documents/Python{}'
langs = {
    'python': [f'python3.7 {execFile}'],
}
# execFile = '/home/noperm/exec'
# langs = {
# 	'python': ['python']
# }

def getBegin(s):
    if len(s) < 2000:
        return s
    else:
        return s[0:2000]


def runCode(lang, code, name, accept, test):
    global langs
    global execFile
    try:
        commands = langs[lang]
        with open(execFile.replace('{}', name), 'w') as f:
            f.write(code)
        outs = ''
        for com in commands:
            # out = sp.run(com, capture_output=True, shell=False, encoding='utf-8', timeout=1)
            with sp.Popen(shlex.split(com.replace('{}', name), posix=False), stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.STDOUT, shell=False, encoding='utf-8') as proc:
                try:
                    outs, errs = proc.communicate(timeout=5)
                except:
                    proc.kill()
                    outs, errs = proc.communicate()
                    outs = getBegin(outs.strip('\n '))+'\nTimed out after 5 seconds'
        accept(outs.strip('\n '))
        return
    except:
        accept('Lang not supported')
        return
num = 0
def runSafe(lang, code, accept, test=None):
    global num
    threading.Thread(target=runCode, args=(lang, code, f'code{num}', accept, test)).start()
    num+= 1

# runCode('python', 'print("hi")', 'exec', print, '')
# print(runCode('python', 'while True:\n\tprint("hi")'))
# com = sp.run('dir', capture_output=True, shell=True, encoding='utf-8')
# print(json.dumps({'content':'```\n'+com.stdout+'\n```'}))
