==========
PyRedstone
==========

Copyright 2012, Josh Gachnang, Josh@ServerCobra.com.

PyRedstone is a Minecraft server wrapper for both vanilla and CraftBukkit servers. It allows you to start/stop the server, manage players, run all in game commands, manage settings and logs, manage CraftBukkit plugins, and a lot more.
PyRedstone also includes a remote API server based on CherryPy that accepts and returns JSON. A reference implementation of a client is included.
The code can be found on `GitHub <https://github.com/pcsforeducation/pyredstone>`_. All issues and pull requests are welcome!

Requirements
============
PyRedstone requires Python 2.7. It has only been tested on Ubuntu, specifically Ubuntu Server 12.04 x64. Additional testing is welcome, and all bugs will be considered. The only Python 2.7 features it relies on are logging.config.dictConfig and OrderedDict.
You must also have Tmux installed. To install it (on Ubuntu), run:
    sudo apt-get update
    sudo apt-get install -y tmux

PyRedstone also relies on the following Python packages:
* cherrypy
* nbt

pyredstone.py
=============
PyRedstone can be run from the commandline like so:
    python pyredstone.py --config /path/to/config status

server.py
=========
The server can be started from the commandline or an init script. A sample init script is include in the package and on Github.
**Note**: The server will attempt to write a PID file to /var/run/pyredstone. The directory must exist and be writable by the user starting the server (root if started by init script).
    python server.py --config /path/to/config

The server accepts JSON in the following format:
**Note**: Username and auth_token are not implemented yet. They will likely be saved in the config file.
    {"username": "USERNAME", "auth_token": "TOKEN", "action": "ACTION", "args": {"arg1": "ARG", "args": "ARG"}}

Config File
===========
The config file is a standard, INI style config file. An example is included called example.cfg. The format should be as follows:
    [ServerName]
    session_name = troydoesntknow
    minecraft_dir = /home/josh/minecraft/
    server_jar = minecraft.jar
    backup_dir = /tmp
    mapper = overviewer

The variables are:
* *session_name*: The name of the Tmux session that will be used.
* *minecraft_dir*: The path to the directory containing *server_jar* and server.properties.
* *server_jar*: The name of the actual Minecraft server jar. The vanilla server is usually minecraft.jar, while CraftBukkit is usually craftbukkit.jar.
* *backup_dir*: Where to put backup files. Not currently used.
* *mapper*: The mapper software. Not currently used.

init.d
======

init.d/minecraft
---------
A standard init wrapper around PyRedstone. It gives the standard '/etc/init.d/minecraft start' interface for services. Acceptable commands are start, stop, restart, update, backup, status, and command. You need to customize USERNAME and CONFIG variables.

init.d/redstone_server
---------------
The redstone_server is an init wrapper for server.py. It allows you to start and stop server.py with the server. Acceptable commands are start, stop, restart, and status. You need to customize the USERNAME and CONFIG variables.