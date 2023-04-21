import subprocess, re, os
from pathlib import Path


class NotifyError(Exception):
    pass


def notify(msg, msg_type='banner', msg_title=None, msg_subtitle=None, msg_action=None, msg_sound=None, msg_button=None, msg_button_action=None, remove_type=None):
    '''notify: Sends banner or alert notifications.

    Args:
        msg (str): message text
        msg_type (str): alert or banner. Defaults to 'banner'.
        msg_title (str, optional): message title. Defaults to None.
        msg_subtitle (str, optional): message subtitle. Defaults to None.
        msg_action (str, optional): The action to be performed when the message is clicked. Either pass 'logout' or path to item to open on click. Can be a .app, file, URL etc. With non-.app items being opened in their default handler. Defaults to None.
        msg_sound (str, optional): sound to play. Pass 'default' for the default macOS sound, else the name of a sound in /Library/Sounds or /System/Library/Sounds. If the sound cannot be found, macOS will use the 'default' sound. Defaults to None.
        msg_button (str, optional): alert type only. Sets the message buttons text. Defaults to None.
        msg_button_action (str, optional): alert type only. The action to be performed when the message button is clicked. Either pass 'logout' or path to item to open on click. Can be a .app, file, URL etc. With non-.app items being opened in their default handler. Requires '--messagebutton' to be passed. Defaults to None.
        remove_type (str, optional): 'prior' or 'all'. If passing 'prior', the full message will be required too. Including all passed flags. Defaults to None.
    '''
    base_dir = os.path.dirname(os.path.realpath(__file__))
    notifier_path = os.path.join(
        base_dir, 'notifier', 'Notifier.app', 'Contents', 'MacOS', 'Notifier')
    notifier_call = [notifier_path, '--message \'' + msg + '\'', '--type \'' + msg_type + '\'']
    if msg_type not in ['alert', 'banner']:
        raise NotifyError('Unknown message type: ' + msg_type + '. Allowed types \'alert\' & \'banner\'')
    if msg_title:
        notifier_call += ['--title \'' + msg_title + '\'']
    if msg_subtitle:
        notifier_call += ['--subtitle \'' + msg_subtitle + '\'']
    if msg_title:
        notifier_call += ['--title \'' + msg_title + '\'']
    if msg_action:
        notifier_call += ['--messageaction \'' + msg_action + '\'']
    if msg_sound:
        notifier_call += ['--sound \'' + msg_sound + '\'']
    if msg_type == 'alert':
        if msg_button:
            notifier_call += ['--messagebutton \'' + msg_button + '\'']
        if msg_button_action:
            notifier_call += ['--messagebuttonaction \'' + msg_button_action + '\'']
    if remove_type:
        if remove_type in ['all', 'prior']:
            notifier_call += ['--remove \'' + remove_type + '\'']
        else:
            raise NotifyError('Unknown remove type: ' + remove_type + '. Allowed types \'all\' & \'prior\'')
    subprocess.run(' '.join(notifier_call), shell=True)


def main():
    regex_devices = '^\(Hardware Port: ([A-Za-z0-9\.\-\/ ]+), Device: (en\d+)\)$'
    regex_device_status = '\tstatus: (inactive|active)$'
    devices = []
    for line in subprocess.check_output(['networksetup', '-listnetworkserviceorder']).decode('utf-8').split('\n'):
        device_match = re.match(regex_devices, line)
        if device_match:
            try:
                ifconfig = subprocess.check_output(['ifconfig', device_match.groups()[1]], stderr=subprocess.STDOUT).decode('utf-8').split('\n')
                status_match = re.match(regex_device_status, ifconfig[-2])
                devices.append({'name': device_match.groups()[0], 'device': device_match.groups()[1], 
                                'status': status_match.groups()[0]})
            except subprocess.CalledProcessError as err:
                # Filter out non IP Devices (e.g. iPhone USB)
                if 'interface ' + device_match.groups()[1] + ' does not exist' not in err.output.decode('utf-8'):
                    raise err

    for dev in devices:
        if re.match('wi\-?fi', dev['name'], re.IGNORECASE):
            dev['type'] = 'wifi'
        else:
            dev['type'] = 'ethernet'

    prev_eth_conn_path = Path('/tmp/toggle-wifi_prev_eth_conn')

    prev_eth_conn = prev_eth_conn_path.is_file()
    eth_conn = bool([x for x in devices if x['status'] == 'active' and x['type'] == 'ethernet'])
    wifi_conn = bool([x for x in devices if x['status'] == 'active' and x['type'] == 'wifi'])

    if not prev_eth_conn and eth_conn and wifi_conn:
        for dev in [x for x in devices if x['status'] == 'active' and x['type'] == 'wifi']:
            subprocess.run(
                ['networksetup', '-setairportpower', dev['device'], 'off'])
            wifi_conn = False
            notify('Ethernet is connected', msg_title='Wifi toggled', msg_subtitle='Wifi is turned off')

    if prev_eth_conn and not eth_conn and not wifi_conn:
        dev = [x for x in devices if x['status'] == 'inactive' and x['type'] == 'wifi'][0]
        subprocess.run(
            ['networksetup', '-setairportpower', dev['device'], 'on'])
        wifi_conn = True
        notify('Ethernet is disconnected', msg_title='Wifi toggled', msg_subtitle='Wifi is turned on')

    if eth_conn:
        prev_eth_conn_path.touch()
    else:
        prev_eth_conn_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
