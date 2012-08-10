#!/usr/bin/env python
import subprocess
import time
import datetime
import sys
import os
import shutil
import urllib2
import socket
import collections
import logging.config
import logconfig
from nbt.nbt import NBTFile
import configurator
import filecmp
from magplus.magplus import MinecraftAssetsGetter
import random
import string
import linux_metrics as lm


# Config with logging config file
logging.config.dictConfig(logconfig.LOGGING)
logger = logging.getLogger('pyredstone')
_version = '0.0.2'

now = datetime.datetime.now()
year = now.strftime("%y")
week = now.strftime("%U")

server_defaults = {"session_name": "troydoesntknow",
"minecraft_dir": "/home/minecraft/minecraft",
"server_jar": "vanilla.jar",
"backup_dir": "/tmp",
"mapper": "overviewer",
"memory_min": "512",
"memory_max": "1024",
"java_args": "-XX:+AggressiveOpts",
"debug": "False",
"stable_releases": "False",
}


# Custom exceptions
# Messages logged here will likely be shown in
class MinecraftException(Exception):
    def __init__(self, msg,):
        self.msg = msg
        #self.code = code

    def __str__(self):
        return "%d: %s" % (self.msg)


class MinecraftCommandException(MinecraftException):
    pass


class NotBukkitException(MinecraftException):
    def __init__(self, message):
        super(NotBukkitException, self).__init__(message,)


class RedstoneServer:
    def __init__(self, config_file):
        """ Create a new server wrapper based on config_file
        Config file must be specified. The required variables are
        minecraft_dir and server_jar. The rest are optional and
        will be set to defaults if not specified.
        """
        if not os.path.exists(config_file):
            raise SyntaxError("Could not find config file. Cannot continue.")
        logger.info('Asking configurator for config from %s' % config_file)
        config = configurator.get_config(config_file)

        # Check for required bits of config.
        if 'minecraft_dir' not in config or 'server_jar' not in config:
            raise SyntaxError("Config file must specify minecraft_dir and server_jar")
        # Check that minecraft_dir does exist. If not, try to make.
        if not os.path.exists(config['minecraft_dir']):
            try:
                os.mkdir(config['minecraft_dir'])
            except EnvironmentError as e:
                logger.exception("Could not create minecraft_dir %s" % config['minecraft_dir'])
                raise SyntaxError("Could not create minecraft_dir %s" % config['minecraft_dir'])
        # Check that the server_jar is in the minecraft_dir. Otherwise, install! (Fail until install ready..)
        if not os.path.exists(os.path.join(config['minecraft_dir'], config['server_jar'])):
            logger.error("server_jar %s is not in minecraft_dir %s. Cannot continue." % (config['server_jar'], config['minecraft_dir']))
            raise SyntaxError("server_jar %s is not in minecraft_dir %s. Cannot continue." % (config['server_jar'], config['minecraft_dir']))
        # Set class attributes either from config or defaults if config doesn't have them.
        for key, value in server_defaults.items():
            if key not in config:
                logger.debug("Setting %s to default: %s" % (key, value))
                setattr(self, key, value)
            else:
                logger.debug("Setting %s: %s" % (key, config[key]))
                setattr(self, key, config[key])

    ###
    # Convenience functions
    ###

    def _call(self, cmd):
        """ Shell call convenience function.
        cmd: A command line string, exactly as would be executed on a shell.
        Returns True for successful execution, False for non-zero command output.
        """
        try:
            subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            #print e.returncode, e.output
            #logger = logging.getLogger('pyredstone')
            #logging.exception("Command call error")
            raise MinecraftCommandException("Command '%s' failed with exit code: %d" % (cmd, e.returncode))

    def console_cmd(self, msg):
        """ Sends a message to the server console. """
        cmd = 'tmux send -t %s "%s" "enter"' % (self.session_name, msg)
        self._call(cmd)

    def _is_ip(self, ip):
        """ Convenience function to determine if a string is an IP or not. """
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False

    #TODO actually implement Twitter
    def twitter_say(self, message):
        if len(message) > 140:
            return False
        else:
            return True

    def _sanitize_log_line(self, line):
        """ Internal function to get rid of the hex and other
        random characters from logging files so they can be displayed
        to users.
        """
        line = line.replace('\x1b[0m', '')
        line = line.replace('\x1b[35m', '')
        line = line.replace('\x1b[35;1m', '')
        line = line.replace('\x1b[m', '')
        line = line.replace('\n', '')
        return line

    def download_file(self, url, output):
        u = urllib2.urlopen(url)
        print output
        f = open(output, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (output, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,

        f.close()

    def test(self):
        """ Here just for testing config and such. """
        pass

    ###
    # Server commands
    ###

    def server_start(self):
        """ Starts the Minecraft server with args from config file.
        Makes a warning log entry if already running and returns.
        """

        if self.status():
            logger.warning("Server already running.")
            return
        if self.java_args is None:
            cmd = 'tmux new -d -s %s "cd %s; java -Xms%dM -Xmx%sM -jar %s nogui"' % (self.session_name, self.minecraft_dir, int(self.memory_min), int(self.memory_max), self.server_jar)
        else:
            cmd = 'tmux new -d -s %s "cd %s; java -Xms%dM -Xmx%sM %s -jar %s nogui"' % (self.session_name, self.minecraft_dir, int(self.memory_min), int(self.memory_max), self.java_args, self.server_jar)
        # Cannot use normal call command. Check output fails with tmux creation.
        try:
            subprocess.call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            #print e.returncode, e.output
            #logger = logging.getLogger('pyredstone')
            #logging.exception("Command call error")
            raise MinecraftCommandException("Command '%s' failed with exit code: %d" % (cmd, e.returncode))
        #print "Minecraft started in tmux session %s" % self.session_name
        logger.info("Server started successfully.")
        return True

    def server_stop(self, quick=False, msg=None):
        """ Stops the server, optionally giving warning messages.
        If quick is True, the server will give a one minute warning to players.
        Returns False if the server isn't running, or if any of the the calls to
        shutdown or message the players fail.

        """
        if not self.status():
            logger.warning("Server is already stopped.")
            return
        if msg:
            self.console_cmd("Say %s" % msg)
        if not quick:
            logger.info("Server going down in 1 minute.")
            result = self.console_cmd("say Server going down in 1 minute")
            time.sleep(30)
            logger.info("Server going down in 30 seconds.")
            cmd = self.console_cmd("say Server going down in 30 seconds")
            time.sleep(15)
            logger.info("Server going down in 15 seconds.")
            cmd = self.console_cmd("say Server going down in 15 seconds")
            time.sleep(15)
        self.console_cmd("stop")
        logger.info("Server successfully stopped.")
        return True

    def server_restart(self, quick=False, msg=None):
        """ Restarts the server, optionally giving warning messages.
        If quick is True, the server will give a one minute warning to players.
        Returns self.status()
        """

        if self.status():
            self.server_stop(quick, msg=msg)
            while self.status():
                time.sleep(1)
        return self.server_start()

    def status(self):
        """ Checks whether the Minecraft server is running.
        Returns True if running, False otherwise.
        """
        try:
            # The second column of each entry is a pid. See if that pid is in /proc/. Obviously Linux centric..
            #TODO update for screen and other ways of running Minecraft.
            out = subprocess.check_output('ps aux | grep  tmux | grep "%s"' % self.session_name, shell=True)
            pids = out.split('\n')
            for pid in pids:
                if len(pid.split()) < 2:
    #                print "invalid pid? %s" % pid.split()
                    continue
                if os.path.exists('/proc/%s' % pid.split()[1]):
                    return True

            return False
        except subprocess.CalledProcessError, e:
            #print e.returncode
            return False

    def update(self):
        """ Find latest version of server, compare to latest released version,
        if there is a newer version, download and replace. If no version
        number can be found, download the latest.
        """
        # Choose between vanilla and bukkit
        download_list = []
        mag = MinecraftAssetsGetter()
        # Determine Jar type
        if self.server_jar == 'vanilla.jar' or self.server_jar == 'minecraft_server.jar':
            jar = 'vanilla'

        elif self.server_jar == 'craftbukkit.jar' or self.server_jar == 'bukkit.jar':
            jar = 'bukkit'
        else:
            logger.error("server_jar is an unsupported version. Expect \
            'vanilla.jar', 'minecraft_server.jar', ''craftbukkit.jar', or \
            'bukkit.jar'. Got %s." % (self.server_jar))
            raise SyntaxError("server_jar is an unsupported version. Expect \
            'vanilla.jar', 'minecraft_server.jar', ''craftbukkit.jar', or \
            'bukkit.jar'. Got %s." % (self.server_jar))

        if self.stable_releases == "True":
            stable = True
            logger.info("Starting update for server type: %s - Stable" % (jar,))
        elif self.stable_releases == "False":
            stable = False
            logger.info("Starting update for server type: %s - Unstable" % (jar,))
        else:
            logger.error("Stable releases must be either 'True' or 'False'. Got %s." % (self.stable_releases))
            raise SyntaxError("Stable releases must be either 'True' or 'False'. Got %s." % (self.stable_releases))

        # Find the existing version from the versions file in the minecraft_dir
        versions_file = os.path.join(self.minecraft_dir, 'version.txt')
        if os.path.exists(versions_file):
            # Version file exists, we can proceed with comparison.
            try:
                with open(versions_file, 'r') as f:
                    current_version = f.readline()
            except IOError as e:
                logger.exception("Could not read version file.")
                raise IOError("Could not read version file %s" % versions_file)
        else:
            # No version file, just download new version.
            current_version = None
        logger.info("Current version is %s" % (current_version,))

        # Get the link to the newest version.
        if jar == 'vanilla':
            ret = mag.getNewerVanillaVersion(current_version, stable)
            if ret is None:
                return
            logger.debug(ret)
            latest_version = mag.getVanillaServerUrl(ret['version'])
        else:
            ret = mag.getNewerBukkitVersion(current_version, stable)
            if ret is None:
                return
            latest_version = ret['download_link']

        logger.info("New version download link: %s" % (latest_version))
        # Create a temp folder
        random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(16))
        try:
            os.mkdir(os.path.join('/tmp', random_string))
        except EnvironmentError as e:
            logger.error("Cannot create temporary folder %s" % (os.path.join('/tmp', random_string)))
            raise OSError("Cannot create temporary folder %s" % (os.path.join('/tmp', random_string)))
        logger.info("Created temp directory %s" % (os.path.join('/tmp', random_string),))

        # Download the file to the temp folder
        self.download_file(latest_version, os.path.join('/tmp', random_string, self.server_jar))
        if os.path.exists(os.path.join('/tmp', random_string, self.server_jar)):
            logger.info("Downloaded file to %s" % os.path.join('/tmp', random_string, self.server_jar))
        else:
            logger.error("Download from %s to %s failed." % (latest_version, os.path.join('/tmp', random_string, self.server_jar)))
            raise OSError("Download from %s to %s failed." % (latest_version, os.path.join('/tmp', random_string, self.server_jar)))

        # Backup the existing server_jar to server_jar.bak
        if os.path.exists(os.path.join(self.minecraft_dir, self.server_jar)):
            try:
                shutil.move(os.path.join(self.minecraft_dir, self.server_jar), os.path.join(self.minecraft_dir, self.server_jar + '.bak'))
            except shutil.Error as e:
                logger.error("Could not move old server_jar %s" % (os.path.join(self.minecraft_dir, self.server_jar)))
                raise OSError("Could not move old server_jar %s" % (os.path.join(self.minecraft_dir, self.server_jar)))
        logger.info("Backed up exist jar %s to %s." % (os.path.join(self.minecraft_dir, self.server_jar), os.path.join(self.minecraft_dir, self.server_jar)))

        # Move the new server_jar from the temp folder to the minecraft_dir
        try:
            shutil.move(os.path.join('/tmp', random_string, self.server_jar), os.path.join(self.minecraft_dir, self.server_jar))
        except shutil.Error as e:
            logger.error("Could not move new server_jar %s to replace old server_jar %s" %(os.path.join()))
            raise OSError("Could not move new server_jar %s to replace old server_jar %s" %(os.path.join()))
        logger.info("Moved new jar to %s. Restart server to complete update." % (os.path.join(self.minecraft_dir, self.server_jar),))

    def uptime(self):
        ''' Returns the time the server host has been running since last reboot. '''
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                uptime_string = str(datetime.timedelta(seconds = uptime_seconds))

            return uptime_string
        except EnvironmentError as e:
            logger.exception("Could not get uptime.")
            raise MinecraftException("Could not get uptime.")

    def server_load(self):
        ''' Average load on the server. '''
        try:
            return os.getloadavg()
        except EnvironmentError as e:
            logger.exception("Could not get load.")
            raise MinecraftException("Could not get load.")

    def server_memory(self):
        ''' Returns memory in form: usedMB/totalMB. '''
        # Get total free
        mem_dict = {}
        popen = os.popen("free -m").readlines()
        mem_dict['total'] = popen[1].split()[1]
        mem_dict['free'] = popen[1].split()[3]
        mem_dict['used'] = popen[1].split()[2]
        mem_dict['used_minus_cache'] = popen[2].split()[2]
        mem_dict['free_minus_cache'] = popen[2].split()[3]
        return mem_dict

    def server_stats(self, disk='sda', net='eth0', sample_duration=0.1):
        """ Returns a dict of stats about the server, including CPU, memory,
        disk and networking activity. Disk is a disk device in /dev, net is
        the name of a networking device. Sample duration is how long the sampling
        will take. 0.1 is low but will provide a better user experience through
        a web interface.

        {procs_running: number of processes currently running
        cpu_use: CPU usage as a percentage.
        cpu_iowait: Percent of time waiting for I/O in CPU time.
        disk_busy: Amount of time the disk is busy
        disk_reads: Total disk reads since last reboot
        disk_writes: Total disk writes since last reboot.
        }

        """
        stats_dict = {}
        stats_dict['procs_running'] = lm.cpu_stat.procs_running()
        cpu_stats = lm.cpu_stat.cpu_percents(sample_duration)
        stats_dict['cpu_use'] = 100 - cpu_stats['idle']
        stats_dict['cpu_iowait'] = cpu_stats['iowait']
        stats_dict['disk_busy'] = lm.disk_stat.disk_busy(disk, sample_duration)
        #r, w = lm.disk_stat.disk_reads_writes(disk)
        #stats_dict['disk_reads'] = r
        #stats_dict['disk_writes'] = w
        used, total = lm.mem_stat.mem_stats()
        # In Megabytes
        stats_dict['mem_used'] = used / 1048576
        stats_dict['mem_total'] = total / 1048576
        # In Kilobits
        rx_bits, tx_bits = lm.net_stat.rx_tx_bits(net)
        stats_dict['net_tx'] = tx_bits / 1000
        stats_dict['net_rx'] = rx_bits / 1000
        print stats_dict
    ###
    # Server Settings
    ###

    # TODO possible solution for ordering of YAML:
    # http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
    def parse_settings(self, filename):
        """ Parses filename into a dict. Filename should be the relative path to
        the settings file from self.minecraft_dir. Settings file can be a YAML
        file, key=value list, or a standard config file. Returns a dict if parsing
        is successful. Raises a MinecraftException otherwise.
        """
        # Get full filename and path. Accepts full path, file in self.minecraft_dir
        # or config.yml/config,txt file in plugin directory in self.minecraft_dir
        if not os.path.exists(filename):
            if os.path.exists('%s/%s' % (self.minecraft_dir, filename)):
                filename = '%s/%s' % (self.minecraft_dir, filename)
            elif os.path.exists('%s/plugins/%s/config.yml' % (self.minecraft_dir, filename)):
                filename = '%s/plugins/%s/config.yml' % (self.minecraft_dir, filename)

            elif os.path.exists('%s/plugins/%s/config.txt' % (self.minecraft_dir, filename)):
                filename = '%s/plugins/%s/config.txt' % (self.minecraft_dir, filename)
            else:
                # Filename doesn't exist or plugin directory/ doesn't exist
                raise MinecraftException("Filename %s does not exist." % (filename,))

        if filename[-4:] == '.yml':
            # Assume yaml
            try:
                import yaml
            except ImportError:
                raise MinecraftException("Could not import YAML for file %s" % (filename,))
            try:
                return yaml.load(open(filename))
            except yaml.YAMLError, e:
                raise MinecraftException("Could not parse YAML file %s" % (filename,))
        # Assume list or key=value
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
        except IOError, e:
            raise MinecraftException("Could not read file %s" % (filename,))

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

    def parse_minecraft_settings(self, filename='server.properties'):
        """ Parses the main server.properties file. Can be used to parse other
        files of the same format. Returns a dict of the settings, or raises
        a MinecraftException if there is an error.
        """
        #p = {}
        p = collections.OrderedDict()
        with open("%s/%s" % (self.minecraft_dir, filename)) as props:
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

    def write_minecraft_settings(self, props, filename='server.properties'):
        """ Writes out a minecraft settings/config file. Can be used for the
        main config file or for plugin files. Takes a dict as props and
        a filename relative to self.minecraft_dir.

        Raises IOError if the file cannot be written
        Raises SyntaxError if the given dict cannot be coerced into the settings
        format
        """
        # Check if original file is yaml or equals-separated
        print type(props)
        original_props = self.parse_minecraft_settings()
        print original_props
        try:
            with open("%s/%s" % (self.minecraft_dir, filename), 'w') as f:
                for key in original_props:
                    print type(original_props), key
                    if key in props:
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
        except IOError as e:
            logger.exception()
        return True

    def rotate_logs(self, quick=False):
        """ Rotates logs from server.log to logs/server.log-YYYY-MM-DD.counter
        """
        # Check that log file exists
        log_file = os.path.join(self.minecraft_dir, 'server.log')
        if not os.path.exists(log_file):
            raise MinecraftException("No log file at %s" % log_file)
        logs_dir = os.path.join(self.minecraft_dir, 'logs')
        # Create logs_dir if it does not exist.
        if not os.path.exists(logs_dir):
            try:
                os.mkdir(logs_dir)
            except EnvironmentError as e:
                raise MinecraftException("Logs directory %s did not exists and could not be created." % logs_dir)
        # Can't rotate logs if server is running.
        if self.status():
            self.server_stop(quick=quick)
        # Move server.logs into logs/ with name based on date. First check to see if same name exists.
        old_log_file = os.path.join(logs_dir, 'server.log' + '-' + datetime.date.today().isoformat())
        counter = 0
        # If old_log_file exists, find a new logfile name, in form of logs/server.log-YYYY-MM-DD.counter
        while os.path.exists(old_log_file):
            old_log_file = os.path.join(logs_dir, 'server.log' + '-' + datetime.date.today().isoformat() + '.' + counter)
            counter = counter + 1
        # Move the log file
        try:
            shutil.move(log_file, old_log_file)
        except shutil.Error as e:
            raise MinecraftException("Could not rotate log from %s to %s" % (log_file, old_log_file))
        # 
        self.server_start()

    ###
    # In game status (NBT)
    ###

    def get_spawn(self):
        """ Finds the spawn coordinates. Returns a 3tuple of ints in the format
        (X, Y, Z) or None if the coordinates cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            return (n[0]["SpawnX"].value, n[0]["SpawnY"].value, n[0]["SpawnZ"].value)

    def get_seed(self):
        """ Finds the seed of the server. Returns the seed as a string, or
        None if the seed cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            return n[0]["RandomSeed"].value

    def is_thundering(self):
        """ Checks if it is currently thundering in game. Returns True if
        thundering, False if not thundering, and None if the thundering state
        cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            if n[0]["thundering"].value == 0:
                return False
            elif n[0]["thundering"].value == 1:
                return True

    def is_raining(self):
        """ Checks if it is currently raining in game. Returns True if
        raining, False if not raining, and None if the raining state
        cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            if n[0]["raining"].value == 0:
                return False
            elif n[0]["raining"].value == 1:
                return True

    def get_time(self):
        """ Gets the current in game time. Returns the time as an int between
        0 and 23999, or None if the time cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            return n[0]["Time"].value % 24000

    def get_day(self):
        """ Gets the current number of elapsed in game days. Returns the days
        as an int, or None if the days cannot be found.
        """
        n = NBTFile('%s/%s/level.dat' % (self.minecraft_dir, self.session_name))
        if n == None:
            return None
        else:
            return n[0]["Time"].value / 24000

    def start_weather(self):
        """ Starts a downfall in the server. Fails silently if already
        downfalling. """
        if self.is_raining():
            logger.warning("Tried to start weather, but already in the middle of a downfall.")
        else:
            self.console_cmd("toggledownfall")

    def stop_weather(self):
        """ Stops a downfall in the server. Fails silently if already
        stopped. """
        if not self.is_raining():
            logger.warning("Tried to stop weather, but downfall is already stopped.")
        else:
            self.console_cmd("toggledownfall")

    def set_time(self, time):
        """ Changes the tie in the server to time. Time must be between 0
        and 24000. 0 is dawn, 6000 is midday, 12000 is dusk, and 18000 is
        midnight. Raises MinecraftException if time is not between 0 and
        24000 (inclusive).
        """
        try:
            time = int(time)
        except ValueError as e:
            logger.error("Got unknown value for set_time. Needs to be an int or able to be cast as an int.")
            raise MinecraftException("Got unknown value for set_time. Needs to be an int or able to be cast as an int.")
        if time < 0 or time > 24000:
            #print "Invalid time, must be between 0 and 24000."
            logger.error("Tried to set time to invalid time %d" % (time,))
            raise MinecraftException("Tried to set time to invalid time %d" % (time,))
        self.console_cmd("time set %s" % (str(time)))

    def get_players(self):
        """ Returns a list of players currently connected to the server.
        """
        self.console_cmd("list")
        count = 0
        ret_list = []
        with open("%s/server.log" % self.minecraft_dir, "r") as f:
            f.seek (0, 2)           # Seek @ EOF
            fsize = f.tell()        # Get Size
            f.seek(max(fsize-1024, 0), 0) # Set pos @ last n chars
            lines = f.readlines()       # Read to end

        lines = list(reversed(lines[-20:]))    # Get last 10 lines
        # This returns True if any line is exactly find_str + "\n"
        for line in lines:
            if "players online:" in line and count < 20:
                #print "Winning line: #", count, " ", line
                # Find the number of players.
                for chars in line.split():
                    if '/' in chars:
                        connected, max_players = chars.split('/')
                        #print connected, max_players
                        #print lines[count - int(connected):count]
                        players = lines[count - int(connected):count]
                        for player in players:
                            stripped_player = player.replace('\x1b[m', '').strip()
                            ret_list.append(stripped_player)
                            #print "Stripped ", stripped_player
                        return ret_list
            # Code for 1.2.5 and previous..
            if "Connected players" in line and count < 20:
                #print "winning line: ", line[:-5]
                players = line[:-4].split()[5:]
            elif count >= 20:
                break
            else:
                count += 1
                #print "Odd line ", line
                continue
            # Remove commas from players
            for player in players:
                ret_list.append(player.replace(',', '', 1))
            break
        return ret_list

    def get_player_skin(self, player):
        """ Get the URL to a player's skin, or None if does not exist.
        """
        conn = httplib.HTTPConnection('http://s3.amazonaws.com/MinecraftSkins/%s.png' % player)
        conn.request('HEAD', path)
        response = conn.getresponse()
        conn.close()
        if response.status == 200:
            return 'http://s3.amazonaws.com/MinecraftSkins/%s.png' % player
        else:
            return None

    def get_player_inventory(self, player):
        n = self._get_player_nbt(player)
        #n = NBTFile('/home/josh/Downloads/servercobra.dat')

        inv_list = []
        inv = n["Inventory"]
        for item in inv:
            #print(item.pretty_tree())
            inv_dict = {}
            inv_dict['id'] = item['id'].value
            if 'Count' in item:
                inv_dict['count'] = item['Count'].value
            else:
                logger.warning("No count?")
            if 'Slot' in item:
                inv_dict['slot'] = item['Slot'].value
            else:
                logger.warning("No slot?")
            if 'tag' in item:
                inv_dict['enchantments'] = {}
                if 'ench' in item['tag']:
                    for ench in item['tag']['ench']:
                        inv_dict['enchantments']['id'] = ench['id'].value
                        inv_dict['enchantments']['level'] = ench['lvl'].value
            inv_list.append(inv_dict)
        return inv_list

    def get_player_location(self, player):
        n = self._get_player_nbt(player)
        loc_list = n["Pos"]
        return (loc_list[0].value, loc_list[1].value, loc_list[2].value)

    def get_player_spawn(self, player):
        n = self._get_player_nbt(player)
        return (n["SpawnX"].value, n["SpawnY"].value, n["SpawnZ"].value)

    def get_player_health(self, player):
        n = self._get_player_nbt(player)
        return n["Health"].value

    def get_player_xp(self, player):
        n = self._get_player_nbt(player)
        return n["XpLevel"].value

    def _get_player_nbt(self, player):
        self.console_cmd("save-all")
        nbt_file = os.path.join(self.minecraft_dir, self.session_name, 'players', player + '.dat')
        if not os.path.exists(nbt_file):
            raise MinecraftException("Could not find player file for player: %s" % player)
        return NBTFile(nbt_file)

    def delete_player_item(self, player, slot):
        """ Will delete everything in the given slot from the player's inventory. """
        pass

    def get_logs(self, num_lines=-1, log_filter=None, chat_filter=None):
        """ Get a number of lines from the log in reverse order (-1 for all).
        log_filter can be chat, players, or None.
        chat_filter will only return player chat.
        TODO add advanced filtering.
        """
        if log_filter not in ('chat', 'players', None):
            #print "Invalid filter."
            return None

        logfile = "%s/server.log" % self.minecraft_dir
        if not os.path.exists(logfile):
            #print "Log file doesn't exists"
            return None

        count = 0
        ret_list = []
        for line in reversed(open(logfile).readlines()):
            if log_filter == 'chat' and "<" in line and ">" in line and "[INFO]" in line:
                l = self._sanitize_log_line(line).split()
                ret_list.append(("chat", l[0], l[1], l[3], " ".join(l[4:])))
                count += 1
            elif log_filter == 'chat' and "[Server]" in line and "World backed up!" not in line and "Server going down in" not in line:
                l = self._sanitize_log_line(line).split()
                ret_list.append(("chat", l[0], l[1], l[3], " ".join(l[4:])))
                count += 1
            elif log_filter == 'players':
                if "logged in" in line or "logged out" in line or "lost connection" in line:
                    l = self._sanitize_log_line(line).split()
                    if "logged in" in line:
                        action = "logged in"
                    elif "logged out" in line or "lost connection" in line:
                        action = "logged out"
                    ret_list.append(("players", l[0], l[1], l[3], action))
                    count += 1
            elif log_filter == None:
                ret_list.append(("none", self._sanitize_log_line(line)))
                count += 1
            if num_lines > 0:
                #print count, num_lines, count < num_lines
                if int(count) >= int(num_lines):
                    #print 'a'
                    break
        return ret_list

    ###
    # Saving
    ###

    def prepare_save(self):
        """ Flushes the server contents to disk, then prevents additional saving
        to the server.
        Returns False if either command false, True otherwise.
        """
        if self.console_cmd("save-all") == False:
            return False
        time.sleep(1)
        self.console_cmd("save-off")

    def after_save(self):
        """ Reenables saving to disk. Useful after backing up the server.
        Returns False if the command fails, True otherwise.
        """
        self.console_cmd("save-on")
        time.sleep(1)
        return True

    ###
    # Player management
    ###

    def set_default_gamemode(self, gamemode):
        """ Changes a player's gamemode. Accepts either 0 (survival), or 1
        (creative) or 2 (adventure) for gamemode. Fails silently if the player
        is not connected.
        """
        try:
            gamemode = int(gamemode)
        except ValueError as e:
            logger.error("Got unknown value for set_default_gamemode. Needs to be an int or able to be cast as an int.")
            raise MinecraftException("Got unknown value for set_default_gamemode. Needs to be an int or able to be cast as an int.")
        if gamemode not in [0, 1, 2, '0', '1', '2', 'creative', 'survival', 'adventure']:
            logger.error("Tried setting default gamemode to unacceptabled gamemode %s." % (str(gamemode),))
            raise MinecraftException("Tried setting default gamemode to unacceptabled gamemode %s." % (str(gamemode),))
        if gamemode == 'survival':
            gamemode = 0
        elif gamemode == 'creative':
            gamemode = 1
        elif gamemode == 'adventure':
            gamemode = 2
        self.console_cmd("defaultgamemode %s" % (str(gamemode)))

    def is_banned(self, player_or_ip, player_type=None):
        """ Checks if a player is currently banned. Player type can be specified,
        otherwise it will attempt to determine if player_or_ip is an IP or player.
        Acceptable values for player_type are "ip", "player" or None.
        Returns True if player is banned, False otherwise.
        """
        if player_type == None:
            if self._is_ip(player_or_ip):
                player_type = 'ip'
            else:
                player_type = 'player'
        if player_type == 'ip':
            f = 'banned-ips.txt'
        else:
            f = 'banned-players.txt'
        with open("%s/%s" % (self.minecraft_dir, f), 'r') as users:
            for user in users:
                if user[:-1] == player_or_ip:
                    # IP already banned
                    return True
        return False

    def get_banned(self, player_type=None):
        """ Gets the list of banned players. If player_type is None, the list
        will contain both IPs and players. Acceptable values for player_type
        are "ip", "player" or None.
        Returns None if there are no banned players or error. Returns a list
        of banned players/IP otherwise.
        """
        user_list = []
        if player_type not in ('player', 'ip', None):
            print "Player must be either 'player', 'ip', or None"
            return None
        if player_type == 'player' or player_type == None:
            with open("%s/%s" % (self.minecraft_dir, 'banned-players.txt'), 'r') as users:
                for user in users:
                    if user == '\n' or user == "None\n":
                        continue
                    if '\n' in user:
                        user_list.append(user[:-1])
                    else:
                        user_list.append(user)
        if player_type == 'ip' or player_type == None:
            with open("%s/%s" % (self.minecraft_dir, 'banned-ips.txt'), 'r') as users:
                for user in users:
                    if '\n' in user:
                        user_list.append(user[:-1])
                    else:
                        user_list.append(user)
        return user_list

    def ban(self, player_or_ip):
        """ Bans a player or IP. Attempts to determine if the arg is
        an IP or player. Returns False if player is already banned
        or banning fails, True otherwise.
        """
        # Check if IP or player:
        if self._is_ip(player_or_ip):
            # IP!
            if self.is_banned(player_or_ip, 'ip'):
                return False
            self.console_cmd("ban-ip %s" % (player_or_ip))
        else:
            # Must be a player..or invalid IP
            if self.is_banned(player_or_ip, 'player'):
                return False
            self.console_cmd("ban %s" % (player_or_ip))
        return True

    def pardon(self, player_or_ip):
        """ Removes the ban on a player or IP. Attempts to determine if the arg is
        an IP or player. Returns False if the player is not banned or server
        command fails, True otherwise.
        """
        # Check if IP or player:
        if self._is_ip(player_or_ip):
            if not self.is_banned(player_or_ip, 'ip'):
                return False
            self.console_cmd("pardon-ip %s" % (player_or_ip))
        else:
            if not self.is_banned(player_or_ip, 'player'):
                return False
            self.console_cmd("pardon %s" % (player_or_ip))

    def op(self, player):
        """ Sets a player to Op. Raises MinecraftCommandException if server
        command fails. Fails silently if player is already op.
        """
        with open("%s/ops.txt" % (self.minecraft_dir), 'r') as users:
            for user in users:
                if user == player:
                    # IP already banned
                    return
        self.console_cmd("op %s" % (player))

    def deop(self, player):
        """ Removes a player from Op self.status. Raises MinecraftCommandException
        if server command fails.
        """

        self.console_cmd("deop %s" % (player))

    def is_op(self, player):
        """ Returns True if player is listed as an Op, False otherwise. """
        return player in self.get_ops()

    def get_ops(self):
        """ Returns a list of Ops, or None if ops file cannot be read. """
        ops = []
        if os.path.exists("%s/ops.txt" % self.minecraft_dir):
            with open("%s/ops.txt" % self.minecraft_dir) as f:
                for user in f:
                    if user[-1] == '\n':
                        ops.append(user[:-1])
                    else:
                        ops.append(user)
            return ops
        logger.error("Could not find an ops file at %s/ops.txt" % self.minecraft_dir)
        raise MinecraftException("Could not find an ops file at %s/ops.txt" % self.minecraft_dir)

    def get_whitelist(self):
        """ Returns a list of whitelisted users or None if there are none. """
        user_list = []
        with open("%s/%s" % (self.minecraft_dir, 'white-list.txt'), 'r') as users:
            for user in users:
                if '\n' in user:
                    user_list.append(user[:-1])
                else:
                    user_list.append(user)
        return user_list

    def disable_whitelist(self):
        """ Disables the whitelist. All users can log in. """
        self.console_cmd("whitelist off")
        return True

    def enable_whitelist(self):
        """ Prevents users not on the whitelist from connecting. Ops may
        always connect. """
        self.console_cmd("whitelist on")
        return True

    # Renew whitelist from disk. Call after adding or removing from whitelist.
    def _whitelist_reload(self):
        """ Reloads the whitelist so changes take affect.
        """
        self.console_cmd("whitelist reload")
        return True

    def add_to_whitelist(self, player):
        """ Adds a player to the whitelist. Returns False if player is already
        on the whitelist. Raises MinecraftCommandException if server command
        fails.
        """
        if player not in self.get_whitelist():
            self.console_cmd("whitelist add %s" % (player))
            self._whitelist_reload()
            return True
        else:
            return False

    def remove_from_whitelist(self, player):
        """ Removes a player from the whitelist. Fails silently if player is
        not on the whitelist. Raises MinecraftCommandException if server command
        fails.
        """
        if player not in self.get_whitelist():
            return False
        self.console_cmd("whitelist remove %s" % (player))
        self._whitelist_reload()
        return True

    ###
    #Plugins
    ###

    def get_plugin_config(self, name):
        """ Given a plugin, tries to find its main config file.
        Raises IOError if the config file cannot be opened.
        Raises SyntaxError if the config file cannot be found.
        """
        # Check for yaml config file
        if os.path.exists("%s/plugins/%s/config.yml" % (self.minecraft_dir, name)):
            try:
                import yaml
            except ImportError:
                print "Couldn't import module 'yaml'"
            return yaml.load(open('%s/plugins/%s/config.yml' % (self.minecraft_dir, name)))    # Check for text config file
        elif os.path.exists("%s/plugins/%s/config.txt" % (self.minecraft_dir, name)):
            p = {}
            try:
                with open("%s/plugins/%s/config.txt" % (self.minecraft_dir, name)) as props:
                    for line in props:
                        s = line.split('=')
                        if len(s) == 2:
                            p[s[0]] = s[1]
                        elif len(s) == 1:
                            p[s[0]] = None
                        else:
                            return None
                return p
            except IOError as e:
                logger.exception("Couldn't open config.txt for plugin %s" % (plugin,))
                raise IOError("Could not open config.txt for plugin %s" % (plugin,))
        # Can't really work on it...
        else:
            #print "can't work on this config file"
            raise SyntaxError("Could not find config file for plugin %s" % (plugin,))

    def list_disabled_plugins(self):
        """ Returns a list of disabled plugins. """
        plugin_list = []
        for ob in os.listdir("%s/plugins_disabled" % self.minecraft_dir):
            if not os.path.isdir("%s/plugins_disabled/%s" % (self.minecraft_dir, ob)) and ob[-4:] == '.jar':
                plugin_list.append(ob[:-4])
        return plugin_list

    def list_plugins(self):
        """ Returns a list of all enabled plugins. """
        plugin_list = []
        for ob in os.listdir("%s/plugins" % self.minecraft_dir):
            if not os.path.isdir("%s/plugins/%s" % (self.minecraft_dir, ob)) and ob[-4:] == '.jar':
                plugin_list.append(ob[:-4])
        return plugin_list

    # Returns True if enabled, False if not enabled
    def is_plugin_enabled(self, name):
        """ Check if plugin is enabled.
        Returns True if plugin is enabled. False otherwise.

        raises NotBukkitException if server is not running Bukkit.
        """

        if self.server_jar == 'vanilla.jar' or self.server_jar == 'minecraft_server.jar':
            raise NotBukkitException("No plugins on vanilla Minecraft server.")
        return name in self.list_plugins()

    def disable_plugin(self, name, reload=True):
        """ If plugin is not already disabled, disables the plugin. If reload
        is True, sends a reload command to the server. Fails silently if
        plugin is already disabled. Case sensitive on plugin name.

        raises NotBukkitException if server is not running Bukkit.
        """
        if self.server_jar == 'vanilla.jar' or self.server_jar == 'minecraft_server.jar':
            raise NotBukkitException("No plugins on vanilla Minecraft server.")
        # Check if plugin is enabled
        if not os.path.exists("%s/plugins/%s.jar" % (self.minecraft_dir, name)):
            print "plugin not enabled"
            return False
        # Check that plugin
        shutil.move("%s/plugins/%s.jar" % (self.minecraft_dir, name), "%s/plugins_disabled/" % (self.minecraft_dir,))
        if os.path.exists("%s/plugins/%s/" % (self.minecraft_dir, name)):
            shutil.move("%s/plugins/%s/" % (self.minecraft_dir, name), "%s/plugins_disabled/" % (self.minecraft_dir,))
        if reload:
            try:
                self.server_reload()
            except MinecraftException as e:
                raise MinecraftException("Plugin was disabled, but reloading failed.")
        #return True

    def enable_plugin(self, name, reload=True):
        """ If plugin is not already enabled, enables the plugin. If reload
        is True, sends a reload command to the server. Fails silently if
        plugin is already enabled. Case sensitive on plugin name.

        raises NotBukkitException if server is not running Bukkit.
        """

        if self.server_jar == 'vanilla.jar' or self.server_jar == 'minecraft_server.jar':
            raise NotBukkitException("No plugins on vanilla Minecraft server.")
        # Check if plugin is already enabled
        if name + '.jar' in os.listdir("%s/plugins" % self.minecraft_dir):
                    print "plugin already enabled"
                    return False
        # Check if plugin exists in disabled
        if not os.path.exists("%s/plugins_disabled/%s.jar" % (self.minecraft_dir, name)):
            print "plugin doesn't exist in disabled directory. Try downloading it first."
            return None
        shutil.move("%s/plugins_disabled/%s.jar" % (self.minecraft_dir, name), "%s/plugins/" % (self.minecraft_dir,))
        if os.path.exists("%s/plugins_disabled/%s/" % (self.minecraft_dir, name)):
            shutil.move("%s/plugins_disabled/%s/" % (self.minecraft_dir, name), "%s/plugins/" % (self.minecraft_dir,))
        if reload:
            try:
                self.server_reload()
            except MinecraftException as e:
                raise MinecraftException("Plugin was enabled, but reloading failed.")
            #return True

    def server_reload(self):
        """ Sends a reload command to the server. This reloads all plugin configs
        and enables or disables plugins.
        """
        try:
            self.console_cmd("reload")
        except MinecraftException as e:
            raise MinecraftException("Reloading the server failed. Error %d" % e.errorcode)

    ###
    # Player Commands
    ###

    def get_player_ip(self, player, every_ip=False):
        """ Gets the last IP a player connected with. If every_ip is True,
        returns a list of IP's the player has connected with (in the current log)
        """
        ip_list = []
        if os.path.exists("%s/server.log" % self.minecraft_dir):
            for line in reversed(open("%s/server.log" % self.minecraft_dir).readlines()):
                if "logged in with entity id" in line and self.session_name in line:
                    # avoid issue where user "josh"'s ip is used for user "joshua".
                    words = line.split()
                    if words[3] == player:
                        ip_line = words[4]
                        # Split at the : for the IP, leave off port, cut off first 2 characters = ip!
                        if every_ip:
                            ip_list.append(ip_line.split(':')[0][2:])
                        else:
                            return ip_line.split(':')[0][2:]

    def kick(self, player):
        """ Kicks a player out of the game. Fails silently if the player is
        not in the game.
        """
        if player not in self.get_players():
            logger.info("Tried to kick player %s, but player was not connected" % (player,))
        self.console_cmd("kick %s" % (player))

    def player_gamemode(self, player, gamemode):
        """ Changes a player's gamemode. Accepts either 0 (survival), 1
        (creative) for gamemode, or 2 (adventure) for gamemode. Fails silently
        if the player is not connected.
        """

        if gamemode not in [0, 1, 2, '0', '1', '2', 'creative', 'survival', 'adventure']:
            logger.error("Tried setting player %s gamemode to unacceptabled gamemode %s." % (player, str(gamemode),))
            raise MinecraftException("Tried setting player %s gamemode to unacceptabled gamemode %s." % (player, str(gamemode),))
        if gamemode == 'survival':
            gamemode = 0
        elif gamemode == 'creative':
            gamemode = 1
        elif gamemode == 'adventure':
            gamemode = 2
        self.console_cmd("gamemode %s %s" % (player, str(gamemode)))

    def server_say(self, message):
        """ Sends an in game message to the players from [CONSOLE].
        Returns False on empty message or failed server command. True otherwise.
        """
        #TODO make this work for other users than [CONSOLE]
        if message == None or message == "":
            #print "No message!"
            return False
        self.console_cmd("say %s" % (message))

    def give(self, player, item_id, num):
        """ Gives player the num item specified by item_id. If num is greater than
        64, it will be split into multiple give commands.
        Returns False if the server commands fail, num is <= 0, or player isn't
        logged in, True otherwise.
        """
        if num <= 0:
            return False
        if player not in self.get_players():
            return False
        while num > 0:
            if num > 64:
                if self.console_cmd("give %s %s %s" % (player, str(item_id), "64")) == False:
                    return False
            else:
                if self.console_cmd("give %s %s %s" % (player, str(item_id), str(num))) == False:
                    return False
            num = int(num) - 64
        return True

    def teleport(self, player, target_player):
        """ Teleports player to target_player.
        Raises MinecraftException if either player is not connected.
        """
        players = self.get_players()
        if player not in players:
            logger.error("Tried to teleport player %s, who is not currently connected." % (player))
            raise MinecraftException("Tried to teleport player %s, who is not currently connected." % (player))
        if target_player not in players:
            logger.error("Tried to teleport other player to player %s, who is not currently connected." % (target_player))
            raise MinecraftException("Tried to teleport other player to player %s, who is not currently connected." % (target_player))
        self.console_cmd("tp %s %s" % (player, target_player))

    def give_xp(self, player, amount):
        """ Gives amount (or removes if amount is negative) XP to player.
        Fails silently if player is not connected.
        Raises MinecraftException if amount is less than -5000 or more than 5000
        """
        if player not in self.get_players():
            logger.info("Tried to give XP to player %s, who is not currently connected." % (player))
        if int(amount) > 5000 or int(amount) < -5000:
            logger.error("XP give amount must be between -5000 and 5000, was %d" % (amount,))
            raise MinecraftException("XP give amount must be between -5000 and 5000, was %d" % (amount,))
        self.console_cmd("xp %s %d" % (player, int(amount)))

    def whisper(self, player, message):
        """ Sends a whisper to a player from the console. Fails silently if
        player is not connected.
        """
        if player not in self.get_players():
            logger.info("Tried to whisper to player %s, who is not currently connected." % (player))
        self.console_cmd("tell %s %s" % (player, message))

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description="A Minecraft server wrapper for vanilla and CraftBukkit servers.")
    parser.add_argument("command", help="The command to call.")
    parser.add_argument("args", nargs="*", help="Args to pass to the command.")
    parser.add_argument("--config", help="Path to config file.")
    args = parser.parse_args()
    if not os.path.exists(args.config):
        logger.error("Config file %s does not exist." % args.config)
        sys.exit(1)
    rs = RedstoneServer(args.config)
    try:
        method = getattr(rs, args.command)
    except AttributeError as e:
        logger.error("%s is not a recognized command. Please try again." % args.command)
        sys.exit(1)
    print method(*args.args)
