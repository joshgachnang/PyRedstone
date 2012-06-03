import subprocess
import time
import datetime
import sys
import os
import shutil
import urllib2
import socket 
import collections

_version = '0.0.1'
session_name = 'troydoesntknow'
minecraft_dir = '/home/josh/minecraft'
bukkit = True
if bukkit:
    minecraft_jar = 'craftbukkit.jar'
else:
    minecraft_jar = 'minecraft_server.jar'
backup_dir = '/home/josh/minecraft_backup'
scp_server = 'josh@thepronserver'
scp_server_target = '/backup/minecraft'

# Debug info
use_test_data = True
test_data = {'status': True, }

def _call(cmd):
    try:
        subprocess.check_output(cmd, shell=True)
        return True
    except CalledProcessError, e:
        #print e.returncode, e.output
        return False
    
def console_cmd(msg):
    if use_test_data:
        return True
    """ Sends a message to the server console. """
    cmd = 'tmux send -t %s "%s" "enter"' % (session_name, msg)
    return _call(cmd) 

#TODO: actually implement Twitter
def twitter_say(message):
    if len(message) > 140:
        return False
    else:
        return True
        
def status():
    if use_test_data:
        return test_data['status']
    try:
        # The second column of each entry is a pid. See if that pid is in /proc/. Obviously Linux centric..
        out = subprocess.check_output('ps aux | grep  tmux | grep "%s"' % session_name, shell=True)
        pids = out.split('\n')
        for pid in pids:
            if os.path.exists('/proc/%s' % pid.split()[1]):
                return True
            
        return False
    except subprocess.CalledProcessError, e:
        #print e.returncode
        return False
        
def server_restart(quick=False):
    """ Gracefully restarts the server. Quick will not give warning messages to users. """
    if status():
        server_stop(quick)
    server_start()
    return status()
    
def server_stop(quick=False):
    """ Gracefully stops the server. Quick will not give warning messages to users. 
    Otherwise, they will be given 1 minute of warning messages.
    
    """
    if use_test_data:
        test_data['status'] == False

    if not status():
        #print "Server isn't running"
        return False
    if not quick:
        if console_cmd("say Server going down in 1 minute") == False:
            return False
        time.sleep(30)
        if console_cmd("say Server going down in 30 seconds") == False:
            return False
        time.sleep(15)
        if console_cmd("say Server going down in 15 seconds") == False:
            return False
        time.sleep(15)
    if console_cmd("say Server going down NOW! See you in 1 minute!") == False:
        return False
    time.sleep(5)
    return console_cmd("stop")

def server_start():
    if use_test_data:
        if test_data['status'] == True:
            return False
        else:
            return True
    if status():
        #print "Server already running in tmux session %s" % session_name
        return False
    cmd = 'tmux new -d -s %s "cd %s; java -Xms1524M -Xmx1524M -jar %s nogui"' % (session_name, minecraft_dir, minecraft_jar)
    _call(cmd)
    time.sleep(5)
    #print "Minecraft started in tmux session %s" % session_name
    return True

def prepare_save():
    """ Stops the server from committing new changes during a save. 
    Returns False if the commands fail, True otherwise.
    
    """
    if console_cmd("save-all") == False:
        return False
    time.sleep(1)
    return console_cmd("save-off")
    
def after_save():
    """ Reenables saving. 
    Returns False if the command fails, True otherwise.
    
    """
    return console_cmd("save-on")

def server_say(message):
    """ Sends a message to the players in the server, which will come from '[CONSOLE]'.
    Return False if the command fails, True otherwise.
    """
    if message == None:
        #print "No message!"
        return False
    return console_cmd("say %s" % message)

def server_quick_stop():
    """ Stops the server without warning to the users.
    Returns False if the server isn't running or the command fails, True otherwise.
    """
    if not status():
        #print "Server isn't running"
        return False
    return console_cmd("stop")
    #print 'Server stopped abruptly'
    
def give(player, item_id, num):
    """ Gives player num amount of item item_id """
    while num > 0:
        if num > 64:
            if console_cmd("give %s %s %s" % (player, item_id, "64")) == False:
                return False
        else:
            if console_cmd("give %s %s %s" % (player, item_id, str(num))) == False:
                return False
        num = int(num) - 64
    return True
    
def update():
    u = urllib2.urlopen('http://minecraft.net/download/minecraft_server.jar')
    f = open('%s/test_update' % minecraft_dir, 'w')
    f.write(u.read())
    f.close()
    testfile = file('%s/test_update' % minecraft_dir, 'rb')
    currentfile = file('%s/minecraft_server.jar' % minecraft_dir, 'rb')
    
    if not zlib.adler32(testfile) == zlib.adler(currentfile):
        server_stop()
        shutil.move('%s/test_update' % minecraft_dir, '%s/minecraft_server' % minecraft_dir)
        server_start()
        return status()
    return True
    
def is_banned(player_or_ip, player_type=None):
    if player_type == None:
        if is_ip(player_or_ip):
            player_type = 'ip'
        else:
            player_type = 'player'
    if player_type == 'ip':
        f = 'banned-ips.txt'
    else:
        f = 'banned-players.txt'
    with open("%s/%s" % (minecraft_dir, f), 'r') as users:
        for user in users:
            if user[:-1] == player_or_ip:
                # IP already banned
                return True
    return False
    
def is_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def get_banned(player_type=None):
    user_list = []
    if player_type not in ('player', 'ip', None):
        print "Player must be either 'player', 'ip', or None"
        return None
    if player_type == 'player' or player_type == None:
        with open("%s/%s" % (minecraft_dir, 'banned-players.txt'), 'r') as users:
            for user in users:
                if user == '\n' or user == "None\n":
                    continue
                if '\n' in user:
                    user_list.append(user[:-1])
                else:
                    user_list.append(user)
    if player_type == 'ip' or player_type == None:
        with open("%s/%s" % (minecraft_dir, 'banned-ips.txt'), 'r') as users:
            for user in users:
                if '\n' in user:
                    user_list.append(user[:-1])
                else:
                    user_list.append(user)
    return user_list
    
def get_whitelist():
    user_list = []
    with open("%s/%s" % (minecraft_dir, 'white-list.txt'), 'r') as users:
        for user in users:
            if '\n' in user:
                user_list.append(user[:-1])
            else:
                user_list.append(user)
    return user_list
    
# Basically a wrapper..
def ban(player_or_ip):
    # Check if IP or player:
    if is_ip(player_or_ip):
        # IP! 
        if is_banned(player_or_ip, 'ip'):
            return None
        return _call('tmux send -t %s "ban-ip %s" "enter"' % (session_name, player_or_ip))
    else:
        # Must be a player..or invalid IP
        if is_banned(player_or_ip, 'player'):
            return None
        return _call('tmux send -t %s "ban %s" "enter"' % (session_name,  player_or_ip))
        
        
def pardon(player_or_ip):
    # Check if IP or player:
    if is_ip(player_or_ip):
        return _call('tmux send -t %s "pardon-ip %s" "enter"' % (session_name, player_or_ip))
    else:
        return _call('tmux send -t %s "pardon %s" "enter"' % (session_name, player_or_ip))
        
def op(player):
    with open("%s/ops.txt" % (minecraft_dir), 'r') as users:
        for user in users:
            if user == player:
                # IP already banned
                return None
    _call('tmux send -t %s "op %s" "enter"' % (session_name, player))
        
def deop(player):
    _call('tmux send -t %s "deop %s" "enter"' % (session_name, player))
    
def add_to_whitelist(player):
    if player not in get_whitelist():
        _call('tmux send -t %s "whitelist add %s" "enter"' % (session_name, player))
        _whitelist_reload()
        
def remove_from_whitelist(player):
    _call('tmux send -t %s "whitelist remove %s" "enter"' % (session_name, player))
    _whitelist_reload()
    
# Returns

# TODO possible solution for ordering of YAML: 
# http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
def parse_settings(filename):
    # Get full filename and path. Accepts full path, file in minecraft_dir
    # or config.yml/config,txt file in plugin directory in minecraft_dir
    if not os.path.exists(filename):
        if os.path.exists('%s/%s' % (minecraft_dir, filename)):
            filename = '%s/%s' % (minecraft_dir, filename)
        elif os.path.exists('%s/plugins/%s/config.yml' % (minecraft_dir, filename)):
            filename = '%s/plugins/%s/config.yml' % (minecraft_dir, filename)
        
        elif os.path.exists('%s/plugins/%s/config.txt' % (minecraft_dir, filename)):
            filename = '%s/plugins/%s/config.txt' % (minecraft_dir, filename)
        else:
            # Filename doesn't exist or plugin directory/ doesn't exist
            print "file doesn't exist"
            return None
            
    if filename[-4:] == '.yml':
        # Assume yaml
        try:
            import yaml
        except ImportError:
            print "Couldn't import module 'yaml'"
        try:
            return yaml.load(open(filename))
        except yaml.YAMLError, e:
            return None
    # Assume list or key=value
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except IOError, e:
        return None
        
    is_kv = False
    # Check list or key=value
    for line in lines:
        # Not exactly deterministic. Good enough for now though.
        if '=' in line:
            is_kv = True
            break
    
    # On return, you can tell if k=v or not by testing type(props).
    # OrderedDict means k=v, list means text list
    if is_kv:
        # key=value
        props = collections.OrderedDict()
        for line in lines:
            if line.strip() == '':
                continue
            if line.strip()[0] == '#' or '=' not in line:
                # No =, or starts with #. Comment! Save anyway
                props[line.strip()] = None
            else:
                # Assume normal key=value
                split = line.strip().split('=')
                if len(split) != 2:
                    #print split
                    # Error. Continue on
                    continue
                props[split[0]] = split[1]
    else:
        # Normal text list
        props = []
        for line in lines:
            print "line: ", line
            if line.strip() == '':
                continue
            if line.strip()[0] == '#':
                # Comment! Not acceptable in list.
                continue
            props.append(line)
    return props
    
def write_settings(filename, properties):
    # First find out if just a list, key=value, or YAML.
    pass

def parse_minecraft_settings(filename='server.properties'):
    #p = {}
    p = collections.OrderedDict()
    with open("%s/%s" % (minecraft_dir, filename)) as props:
        for line in props:
            s = line.split('=')
            if len(s) == 2:
                        p[s[0]] = s[1]
            elif len(s) == 1:
                            p[s[0]] = None
            else:
                #print line
                return None
    return p

def write_minecraft_settings(props, filename='server.properties'):
    # Check if original file is yaml or equals-separated
    print type(props)
    original_props = parse_minecraft_settings()
    print original_props
    with open("%s/%s" % (minecraft_dir, filename), 'w') as f:
        for key in original_props:
            print type(original_props), key
            if props.has_key(key):
                if props[key] == None:
                    if key.lstrip()[0] == '#':
                        f.write(key.strip())
                        if key[-1] != '\n':
                            f.write('\n')
                    else:
                        f.write(key.strip() + '=\n')
                else:
                    f.write("%s=%s\n" % (key.strip(), props[key].strip()))
            else:
                if original_props[key] == None:
                    if key.lstrip()[0] == '#':
                        f.write(key.strip())
                        if key[-1] != '\n':
                            f.write('\n')
                    else:
                        f.write(key.strip() + '=\n')
                else:
                    f.write("%s=%s\n" % (key.strip(), original_props[key].strip()))
    return True

def get_plugin_config(name):
    # Check for yaml config file
    if os.path.exists("%s/plugins/%s/config.yml" % (minecraft_dir, name)):
        try:
            import yaml
        except ImportError:
            print "Couldn't import module 'yaml'"
        return yaml.load(open('%s/plugins/%s/config.yml' % (minecraft_dir, name)))		
    # Check for text config file
    elif os.path.exists("%s/plugins/%s/config.txt" % (minecraft_dir, name)):
        p = {}
        with open("%s/plugins/%s/config.txt" % (minecraft_dir, name)) as props:
            for line in props:
                s = line.split('=')
                if len(s) == 2:
                    p[s[0]] = s[1]
                elif len(s) == 1:
                    p[s[0]] = None
                else:
                    return None
        return p

    # Can't really work on it...
    else:
        #print "can't work on this config file"
        return None
        
# Returns a tuple of ints; (X, Y, Z)
def get_spawn():
    import nbt
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        return (n[0]["SpawnX"].value, n[0]["SpawnY"].value, n[0]["SpawnZ"].value)

def get_seed():
    import nbt
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        return n[0]["RandomSeed"].value
        
def is_thundering():
    import nbt
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        if n[0]["thundering"].value == 0:
            return False
        elif n[0]["thundering"].value == 1:
            return True
        
def is_raining():
    import nbt
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        if n[0]["raining"].value == 0:
            return False
        elif n[0]["raining"].value == 1:
            return True
        
def get_time():
    import nbt
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        return n[0]["Time"].value % 24000

def get_day():
    import nbt