"""User-invoked setup for the per-user macOS background service."""
import os
import plistlib
import socket
import subprocess
import sys
from pathlib import Path

LABEL = 'com.marketdesk.reborn.collector'
LAUNCHCTL = '/bin/launchctl'


def definition(root, python, data):
    return {'Label': LABEL, 'ProgramArguments':[str(python),str(root/'server.py'),'--background'],
            'WorkingDirectory':str(root),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,
            'StandardOutPath':str(data/'collector.log'),'StandardErrorPath':str(data/'collector-errors.log')}


def main():
    if sys.platform!='darwin':sys.exit('This helper is for macOS.')
    path=Path.home()/'Library'/'LaunchAgents'/(LABEL+'.plist')
    domain='gui/'+str(os.getuid())
    target=domain+'/'+LABEL
    loaded=subprocess.run([LAUNCHCTL,'print',target],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if sys.argv[1:]==['disable']:
        if loaded:subprocess.run([LAUNCHCTL,'bootout',target],check=True)
        path.unlink(missing_ok=True)
        print('Background startup disabled. Your saved data is available the next time you start Market Desk.')
        return
    if sys.argv[1:]!=['enable']:sys.exit('Choose enable or disable.')
    if loaded:sys.exit('A Market Desk login service is active. Run Disable Background at Login.command first to upgrade it.')
    try:
        with socket.create_connection(('127.0.0.1',8765),timeout=.5):pass
    except ConnectionRefusedError:pass
    else:sys.exit('Stop the Market Desk Terminal server before enabling background startup.')
    root=Path(__file__).resolve().parent
    data=Path.home()/'.marketdesk-reborn'
    data.mkdir(mode=0o700,exist_ok=True)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.new')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:plistlib.dump(definition(root,Path(sys.executable),data),stream)
    temp.replace(path)
    try:subprocess.run([LAUNCHCTL,'bootstrap',domain,str(path)],check=True)
    except subprocess.CalledProcessError:
        path.unlink(missing_ok=True)
        sys.exit('macOS could not enable the service. Use Start Market Desk.command to collect in Terminal.')
    print('Background startup enabled. Keep this extracted folder at its current location.')
    print('Open http://127.0.0.1:8765 when you want the dashboard.')


if __name__=='__main__':main()
