#!/usr/bin/env python
import cherrypy
import pyredstone
import json
import ast
from cherrypy.process.plugins import Daemonizer, PIDFile
import logging
import logging.config
import logconfig
import os
import sys

logging.config.dictConfig(logconfig.LOGGING)
logger = logging.getLogger('pyredstone')

prohibited_actions = ["_call"]
rs = None

class Root:
    @cherrypy.tools.json_out(on=True)
    @cherrypy.tools.json_in(on=True, )
    def index(self):
        """ Expects a JSON dict to be in cherrypy.request.json. Expected syntax of the JSON:
        {"action": "$action_name", "username": "$username", "auth_token": "$auth_token", "args": {"arg1": "arg1"...}, }
        """
        logger = logging.getLogger('logger')
        if hasattr(cherrypy.request, "json"):
            #logger.error("json", str(cherrypy.request.json), type(cherrypy.request.json), ast.literal_eval(str(cherrypy.request.json)))
            data_in = ast.literal_eval(str(cherrypy.request.json))
            if "username" not in data_in or "auth_token" not in data_in:
                logger.error("Username and/or auth_token not provided.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token not provided.")
            if not self.client_authenticate(data_in["username"], data_in["auth_token"]):
                logger.error("Username and/or auth_token incorrect.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token incorrect.")
            if "config_file" not in data_in:
                logger.error("Config file required!")
                raise cherrypy.HTTPError(403, "Config file required.")
            if not os.path.exists(config_file):
                logger.error("Config file does not exist: %s" % config_file)
                raise cherrypy.HTTPError(403, "Config file does not exist: %s" % config_file)
            try:
                redstone = pyredstone.RedstoneServer(config_file)
            except SyntaxError as e:
                logger.exception("Could not create the redstone server with config file %s." % config_file)
                raise cherrypy.HTTPError(403, "Could not create redstone server with config file %s." % config_file)
            if "action" not in data_in:
                logger.error("Requests require an action.")
                raise cherrypy.HTTPError(400, "Requests require an action.")
            # Decide what args we have
            if "args" not in data_in:
                args = None
            elif "args" == {}:
                args = None
            else:
                args = data_in["args"]
            # Ensure action isn"t in the prohibited list of actions, such as _call, which present a security risk.
            if data_in["action"] in prohibited_actions:
                logger.error("Action %s prohibited" % data_in["action"])
                raise cherrypy.HTTPError(405, "Action %s prohibited" % data_in["action"])
            # Try to get the function from the RedstoneServer. Then pass the arg list.
            try:
                logger.info("Attempting to call RedstoneServer function %s." % (data_in["action"]))
                methodToCall = getattr(redstone, data_in["action"])
                if args is None:
                    result = methodToCall()
                else:
                    result = methodToCall(**args)
                #logger.info("Function %s returned " % data_in["action"], result)
            except AttributeError as e:
                logger.error("Action %s not found." % data_in["action"])
                raise cherrypy.HTTPError(404, "Action not found.")

            logger.debug(data_in)
            return {"result": result}
        else:
            logger.info("Plain GET request")
            if rs.status():
                return "Server is running."
            else:
                return "Server is not running."
            logger.debug("Plain GET request finished.")

    def client_authenticate(self, username, auth_token):
        return True

    @cherrypy.tools.json_out(on=True)
    @cherrypy.tools.json_in(on=True, )
    def batch(self):
        """ Responds with JSON of the form {"action": "result", "other_action": "other_result"} """
        response = {}
        logger.debug("Starting batch request")
        if hasattr(cherrypy.request, "json"):
            #logger.error("json", str(cherrypy.request.json), type(cherrypy.request.json), ast.literal_eval(str(cherrypy.request.json)))
            data_in = ast.literal_eval(str(cherrypy.request.json))
            if "username" not in data_in or "auth_token" not in data_in:
                logger.error("Username and/or auth_token not provided.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token not provided.")
            logger.debug("Username: %s, auth_token: %s." % (data_in['username'], data_in['auth_token']))
            if not self.client_authenticate(data_in["username"], data_in["auth_token"]):
                logger.error("Username and/or auth_token incorrect.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token incorrect.")
            logger.debug("username/auth_token authenticated correctly.")
            if "config_file" not in data_in:
                logger.error("Config file required!")
                raise cherrypy.HTTPError(403, "Config file required.")
            logger.debug("Found config file. Ensuring it exists..")
            if not os.path.exists(data_in['config_file']):
                logger.error("Config file does not exist: %s" % data_in['config_file'])
                raise cherrypy.HTTPError(403, "Config file does not exist: %s" % data_in['config_file'])
            logger.debug("config_file exists: %s" % data_in['config_file'])
            try:
                redstone = pyredstone.RedstoneServer(data_in['config_file'])
            except SyntaxError as e:
                logger.exception("Could not create the redstone server with config file %s." % data_in['config_file'])
                raise cherrypy.HTTPError(403, "Could not create redstone server with config file %s." % data_in['config_file'])
            logger.debug("RedstoneServer created.")
            if "action_list" not in data_in:
                logger.error("Batch requests require an action_list.")
                raise cherrypy.HTTPError(400, "Batch requests require an action_list.")
            # Process each action in action_list
            logger.debug("Found action_list: %s" % data_in["action_list"])
            #PROBLEM STARTS HERE!!!!!!!!!!!!!!!!!
            for items in data_in["action_list"].items():
                print "Items: ", items
                # Check that each action has a command and optional arg list
                if len(items) < 2:
                    logger.error("Improperly formed action list. %s" % items)
                    raise cherrypy.HTTPError(400, "Improperly formed action list. %s" % items)
                if "action" not in items[1]:
                    logger.error("Each item in action_list needs an action.")
                    raise cherrypy.HTTPError(400, "Each item in action_list needs an action.")
                logger.debug("Processing action %s" % items[1])
                action = items[1]["action"]
                if "args" not in items[1]:
                    args = None
                elif "args" == "":
                    args = None
                else:
                    args = items[1]["args"]
                logger.debug("Args for action %s are %s" % (action, args))
                if action in prohibited_actions:
                    logger.error("Action %s prohibited" % action)
                    raise cherrypy.HTTPError(405, "Action %s prohibited" % action)
                # Try to get the function from pyredstone module. Then pass the arg list.
                try:
                    methodToCall = getattr(redstone, action)
                    if args is None or args == "":
                        result = methodToCall()
                    elif isinstance(args, dict):
                        result = methodToCall(**args)
                    else:
                        result = methodToCall(args)
                except AttributeError as e:
                    logger.error("Action %s not found." % action)
                    raise cherrypy.HTTPError(404, "Action %s not found." % action)
                response[action] = result
            logger.debug(response)
            return response
        else:
            logger.info('Plan HTTP status request.')
            if rs.status():
                return "Server is running."
            else:
                return "Server is not running."
    index.exposed = True
    batch.exposed = True

if __name__ == "__main__":
    # Check that run directory exists.
    if not os.path.exists('/var/run/pyredstone/'):
        try:
            os.mkdir('/var/run/pyredstone/')
        except EnvironmentError as e:
            logger.error("Run directory /var/run/pyredstone/ does not exist and cannot be created. Try running 'sudo mkdir /var/run/pyredstone/'.")
            sys.exit(1)
    # Try writing to directory.
    try:
        open('/var/run/pyredstone/test', 'w')
        os.remove('/var/run/pyredstone/test')
    except EnvironmentError as e:
        logger.error("Could not write to run directory /var/run/pyredstone. Try running 'sudo chown -R YOUR_USERNAME /var/run/pyredstone/'.")
        sys.exit(2)
    import argparse
    parser = argparse.ArgumentParser(description="Creates a remote HTTP/JSON API for the PyRedstone wrapper around a Minecraft Server.")
    parser.add_argument("--config", help="Path to PyRedstone config file.")
    args = parser.parse_args()
    if not os.path.exists(args.config):
        logger.error("Config file %s does not exist." % args.config)
        sys.exit(1)
    logger.info("Creating RedstoneServer with config file %s" % (args.config,))
    # Create global RedstoneServer
    rs = pyredstone.RedstoneServer(args.config)
    logger.info("Starting server on 0.0.0.0:7777")

    # Daemonize the server
    d = Daemonizer(cherrypy.engine)
    d.subscribe()
    PIDFile(cherrypy.engine, '/var/run/pyredstone/server.pid').subscribe()
    cherrypy.config.update({"server.socket_host": "0.0.0.0",
                            "server.socket_port": 7777,
                            "log.error_file": "cherrypy.log",
                            "log.access_file": "cherrypy.access",
                            "log.screen_file": "cherrypy.screen",
                            })
    cherrypy.quickstart(Root())
