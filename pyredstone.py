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
       
use_test_data = False

def _call(cmd):
    try:
        subprocess.check_output(cmd, shell=True)
        return True
    except subprocess.CalledProcessError, e:
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
    if status():
        server_stop(quick)
    server_start()
    return status()
    
def server_stop(quick=False):
    if not status():
        #print "Server isn't running"
        return False
    if not quick:
        cmd = console_cmd("say Server going down in 1 minute")
        if _call(cmd) == False:
            return False
        time.sleep(30)
        cmd = console_cmd("say Server going down in 30 seconds")
        if _call(cmd) == False:
            return False
        time.sleep(15)
        cmd = console_cmd("say Server going down in 15 seconds")
        if _call(cmd) == False:
            return False
        time.sleep(15)
        
    cmd = console_cmd("say Server going down NOW! See you in 1 minute!")
    if _call(cmd) == False:
        return False
    time.sleep(5)
    return console_cmd("stop")

def server_start():
    if status():
        #print "Server already running in tmux session %s" % session_name
        return False
    cmd = 'tmux new -d -s %s "cd %s; java -Xms1524M -Xmx1524M -jar %s nogui"' % (session_name, minecraft_dir, minecraft_jar)
    _call(cmd)
    time.sleep(5)
    #print "Minecraft started in tmux session %s" % session_name
    return True

def prepare_save():
    if console_cmd("save-all") == False:
        return False
    time.sleep(1)
    return console_cmd("save-off")
    
def after_save():
    console_cmd("save-on")
    time.sleep(1)
    return True

def server_say(message):
    if message == None:
        #print "No message!"
        return False
    return console_cmd("say %s" % (message))

def server_quick_stop():
    if not status():
        #print "Server isn't running"
        return False
    console_cmd("stop")
    time.sleep(3)
    return True
    #print 'Server stopped abruptly'
    
def give(player, item_id, num):
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
        return console_cmd("ban-ip %s" % (player_or_ip))
    else:
        # Must be a player..or invalid IP
        if is_banned(player_or_ip, 'player'):
            return None
        return console_cmd("ban %s" % ( player_or_ip))
        
        
def pardon(player_or_ip):
    # Check if IP or player:
    if is_ip(player_or_ip):
        return console_cmd("pardon-ip %s" % (player_or_ip))
    else:
        return console_cmd("pardon %s" % (player_or_ip))
        
def op(player):
    with open("%s/ops.txt" % (minecraft_dir), 'r') as users:
        for user in users:
            if user == player:
                # IP already banned
                return None
    console_cmd("op %s" % (player))
        
def deop(player):
    console_cmd("deop %s" % (player))
    
def add_to_whitelist(player):
    if player not in get_whitelist():
        console_cmd("whitelist add %s" % (player))
        _whitelist_reload()
        
def remove_from_whitelist(player):
    console_cmd("whitelist remove %s" % (player))
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
    n = nbt.NBTFile('%s/%s/level.dat' % (minecraft_dir, session_name))
    if n == None:
        return None
    else:
        return n[0]["Time"].value / 24000
        
def list_disabled_plugins():
    plugin_list = []
    for ob in os.listdir("%s/plugins_disabled" % minecraft_dir):
        if not os.path.isdir("%s/plugins_disabled/%s" % (minecraft_dir, ob)) and ob[-4:] == '.jar':
            plugin_list.append(ob[:-4])
    return plugin_list

def list_plugins():
    plugin_list = []
    for ob in os.listdir("%s/plugins" % minecraft_dir):
        if not os.path.isdir("%s/plugins/%s" % (minecraft_dir, ob)) and ob[-4:] == '.jar':
            plugin_list.append(ob[:-4])
    return plugin_list

# Returns True if enabled, False if not enabled
def is_plugin_enabled(name):
    plugins = list_plugins()
    return name in plugins

def disable_plugin(name):
    # Check if plugin is enabled
    if not os.path.exists("%s/plugins/%s.jar" % (minecraft_dir, name)):
        print "plugin not enabled"
        return False
    # Check that plugin 
    shutil.move("%s/plugins/%s.jar"	% (minecraft_dir, name), "%s/plugins_disabled/" % (minecraft_dir, ))
    if os.path.exists("%s/plugins/%s/" % (minecraft_dir, name)):
        shutil.move("%s/plugins/%s/" % (minecraft_dir, name), "%s/plugins_disabled/" % (minecraft_dir, ))
    return True
    
def enable_plugin(name):
    # Check if plugin is already enabled
    if name + '.jar' in os.listdir("%s/plugins" % minecraft_dir):
                print "plugin already enabled"
                return False
    # Check if plugin exists in disabled
    if not os.path.exists("%s/plugins_disabled/%s.jar" % (minecraft_dir, name)):
        print "plugin doesn't exist in disabled directory. Try downloading it first."
        return None
    shutil.move("%s/plugins_disabled/%s.jar" % (minecraft_dir, name), "%s/plugins/" % (minecraft_dir, ))
    if os.path.exists("%s/plugins_disabled/%s/" % (minecraft_dir, name)):
            shutil.move("%s/plugins_disabled/%s/"    % (minecraft_dir, name), "%s/plugins/" % (minecraft_dir, ))
    return True
    
def get_player_ip(player):
    if os.path.exists("%s/server.log" % minecraft_dir):
        for line in reversed(open("%s/server.log" % minecraft_dir).readlines()):
            if "logged in with entity id" in line and session_name in line:
                # avoid issue where user "josh"'s ip is used for user "joshua".
                words = line.split()
                if words[3] == player:
                    ip_line = words[4]
                    # Split at the : for the IP, leave off port, cut off first 2 characters = ip!
                    return ip_line.split(':')[0][2:]

def kick(player):
    if player not in get_players():
        print "Player %s not currently connected." % (player)
        return False
    console_cmd("kick %s" % (player))

def player_gamemode(player, gamemode):
    if gamemode != 0 and gamemode != 1:
        return False
    console_cmd("gamemode %s %s" % (player, gamemode))
    return True
    
def teleport(player, target_player):
    players = get_players()
    if player not in players:
        print "Player %s not currently connected." % (player)
        return False
    if target_player not in players:
        print "Player %s not currently connected." % (target_player)
        return False
    console_cmd("tp %s %s" % (player, target_player))
    return True
    
def give_xp(player, amount):
    if player not in get_players():
        print "Player %s not currently connected." % (player)
        return False
    if int(amount) > 5000 or int(amount) < 5000:
        print "Amount must be between -5000 and 5000"
        return False
    console_cmd("xp %s %d" % (player, int(amount)))

# Renew whitelist from disk. Call after adding or removing from whitelist.
def _whitelist_reload():
    return console_cmd("whitelist reload")

def whisper(player, message):
    if player not in get_players():
        print "Player %s not currently connected." % (player)
        return False
    return console_cmd("tell %s %s" % (player, message))
    
def get_ops():
    ops = []
    if os.path.exists("%s/ops.txt" % minecraft_dir):
        with open("%s/ops.txt" % minecraft_dir) as f:
            for user in f:
                if user[-1] == '\n':
                    ops.append(user[:-1])
                else:
                    ops.append(user)
        return ops
    #print "No ops file"
    return []
    
## Returns True if weather toggled on, False if toggled off.
#def toggle_weather():
    #cmd = console_cmd("toggledownfall" "enter"' % (session_name,)
        #_call(cmd)
    ## Avoid race condition
    #time.sleep(0.5)
    #if os.path.exists("%s/server.log" % minecraft_dir):
        #for line in reversed(open("%s/server.log" % minecraft_dir).readlines()):
            #if "Toggling downfall off" in line and session_name in line:
                    #print line
                    #return False
            #elif "Toggling downfall on" in line and session_name in line:
                    #print line
                    #return True
    #return False
                    
def start_weather():
    if is_raining():
        return False
    else:
        return console_cmd("toggledownfall")
        
def stop_weather():
    if not is_raining():
        return False
    else:
        return console_cmd("toggledownfall")

def set_time(time):
    if time < 0 or time > 24000:
        #print "Invalid time, must be between 0 and 24000."
        return False
    return console_cmd("time set %s" % (str(time)))

def get_players():
    if console_cmd("list") == False:
        return None
    cnt = 0
    ret_list = []
    for line in reversed(open("%s/server.log" % minecraft_dir).readlines()):
        if "Connected players" in line and cnt < 20:
            #print "winning line: ", line[:-5]
            players = line[:-5].split()[5:]
        elif cnt >= 20:
            break
        else:
            cnt += 1
            print line	
            continue
        # Remove commas from players
        for player in players:
            ret_list.append(player.replace(',', '', 1))
        break
    return ret_list

def _santize_log_line(line):
    line = line.replace('\x1b[0m', '')
    line = line.replace('\x1b[35m', '')
    line = line.replace('\n', '')
    return line
    
# Get a number of lines from the log in reverse order (-1 for all).
# Filter
def get_logs(num_lines=-1, filter=None):
    if filter not in ('chat', 'players', None):
        #print "Invalid filter."
        return None
        
    logfile = "%s/server.log" % minecraft_dir
    if not os.path.exists(logfile):
        #print "Log file doesn't exists"
        return None
        
    cnt = 0
    ret_list = []
    for line in reversed(open(logfile).readlines()):
        if filter == 'chat' and "<" in line and ">" in line and "[INFO]" in line:
            l = _santize_log_line(line).split()
            ret_list.append(("chat", l[0], l[1], l[3], " ".join(l[4:])))
            cnt += 1
        elif filter == 'chat' and "[Server]" in line:
            l = _santize_log_line(line).split()
            ret_list.append(("chat", l[0], l[1] , l[3], " ".join(l[4:])))
            cnt += 1
        elif filter == 'players':
            if "logged in" in line or "logged out" in line or "lost connection" in line:
                l = _santize_log_line(line).split()
                if "logged in" in line:
                    action = "logged in"
                elif "logged out" in line or "lost connection" in line:
                    action = "logged out"
                ret_list.append(("players", l[0], l[1], l[3], action))
                cnt += 1
        elif filter == None:
            ret_list.append(("none", _santize_log_line(line)))
            cnt += 1
        if num_lines > 0:
            #print cnt, num_lines, cnt < num_lines
            if int(cnt) >= int(num_lines):
                #print 'a'
                break
    return ret_list

def backup():
    now = datetime.datetime.now()
    if now.minute == 0:
        print "Starting hourly save at hour %d" % now.hour
        prepare_save()
        backup_filename = "%s/%s-hourly-%d.tar.gz" % ( backup_dir, session_name, now.hour,)
        _call('tar czvf %s %s %s %s' % (backup_filename, os.path.join(minecraft_dir, session_name), os.path.join(minecraft_dir, session_name + "_the_end"), os.path.join(minecraft_dir, session_name + "_nether") ))
        #print "World backed up!"
        after_save()
        offsite_backup(backup_filename)
        #print "Offsite backup complete!"
        #return True
    else:
        #print "Script must have been called manually. Making separate backup."
        prepare_save()
        backup_filename = "%s/%s-manual-%d.tar.gz" % ( backup_dir, session_name, now.hour )
        date_string = "%d-%d-%d_%d-%d" % (now.year, now.month, now.day, now.hour, now.minute)
        _call('tar czvf %s %s' % (backup_filename, os.path.join(minecraft_dir, session_name) ))
        #print "World backed up!"
        after_save()
        offsite_backup(backup_filename) 
        #print "Offsite backup complete!"
        #return True
    # Daily backup, will keep 31 copies, then start overwriting.
    if now.hour == 0 and now.minute == 0:
        hourly_backup = "%s/%s-hourly-%d.tar.gz" % ( backup_dir, session_name, now.hour )
        daily_backup = "%s/%s-daily-%d.tar.gz" % ( backup_dir, session_name, now.day )
        try:
            shutil.copy(hourly_backup, daily_backup)
        except Error, e:
            #print e
            return False
    return True

# Assumes you already synced keys to scp_server and can login without a password
def offsite_backup(filename):
    if os.path.exists(filename):
        return _call('scp filename %s:%s' % (scp_server, scp_server_target))
    else:
        #print "Backup file %s didn't exist for offsite backup." % filename
        return False
    
def list_backups():
    pass

def _cli_help():
    pass

if __name__ == '__main__':
    if len(sys.argv) == 1:
        cli_help()
        sys.exit(1)
    #print sys.argv
    try:
        import mccommands
        function=getattr(mccommands, sys.argv[1])
        if len(sys.argv) == 2:
            print function()
        elif len(sys.argv) == 3:
            print function(sys.arv[2])
        elif len(sys.argv) == 3:
            print function(sys.arv[2], sys.arv[3])
        elif len(sys.argv) == 3:
            print function(sys.arv[2], sys.arv[3], sys.arv[4])
        else:
            _cli_help()
    except AttributeError, e:
        print "No such function."
    #print results
