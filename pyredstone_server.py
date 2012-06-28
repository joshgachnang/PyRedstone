#!/usr/bin/env python
import cherrypy
import pyredstone
import json
import ast
from cherrypy.process.plugins import Daemonizer, PIDFile
import logging
from logging.config import dictConfig as dictconfig
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {

        'file_log': {                 # define and name a second handler
            'level': 'DEBUG',
            'class': 'logging.FileHandler', # set the logging class to log to a file
            'formatter': 'verbose',         # define the formatter to associate
            'filename': '/var/log/pyredstone_server.log'  # log file
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'logger': {               # define another logger
            'handlers': ['file_log', 'console'],  # associate a different handler
            'level': 'DEBUG',                 # specify the logging level
            'propagate': True,
        },
    }
}

dictconfig(LOGGING)
logger = logging.getLogger('logger')

prohibited_actions = ["_call"]

class Root:
    @cherrypy.tools.json_out(on=True)
    @cherrypy.tools.json_in(on=True, )
#    @cherrypy.tools.jsonify() 
    def index(self):
        """ Expects a JSON dict to be in cherrypy.request.json. Expected syntax of the JSON:
        {"action": "$action_name", "username": "$username", "auth_token": "$auth_token", "args": {"arg1": "arg1"...}, }
        """
        if hasattr(cherrypy.request, "json"):
            logger.error("json", str(cherrypy.request.json), type(cherrypy.request.json), ast.literal_eval(str(cherrypy.request.json)))
            data_in = ast.literal_eval(str(cherrypy.request.json))
            if "username" not in data_in or "auth_token" not in data_in:
                logger.error("Username and/or auth_token not provided.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token not provided.")
            if not self.client_authenticate(data_in["username"], data_in["auth_token"]):
                logger.error("Username and/or auth_token incorrect.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token incorrect.")
            if "action" not in data_in:
                logger.error("Requests require an action.")
                raise cherrypy.HTTPError(400, "Requests require an action.")
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
            # Try to get the function from pyredstone module. Then pass the arg list.
            try:
                methodToCall = getattr(pyredstone, data_in["action"])
                if args is None:
                    result = methodToCall()
                else:
                    result = methodToCall(**args)
            except AttributeError as e:
                logger.error("Action %s not found." % data_in["action"])
                raise cherrypy.HTTPError(404, "Action not found.")
            
            logger.debug(data_in)
            return {"result": result}
        else:
            logger.info("Plain GET request")
            if pyredstone.status:
                return "Server is running."
            else:
                return "Server is not running."
    
    
    def client_authenticate(self, username, auth_token):
        return True

    @cherrypy.tools.json_out(on=True)
    @cherrypy.tools.json_in(on=True, )  
    def batch(self):
        """ Responds with JSON of the form {"action": "result", "other_action": "other_result"} """
        response = {}
        if hasattr(cherrypy.request, "json"):
            #logger.error("json", str(cherrypy.request.json), type(cherrypy.request.json), ast.literal_eval(str(cherrypy.request.json)))
            data_in = ast.literal_eval(str(cherrypy.request.json))
            if "username" not in data_in or "auth_token" not in data_in:
                logger.error("Username and/or auth_token not provided.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token not provided.")
            if not self.client_authenticate(data_in["username"], data_in["auth_token"]):
                logger.error("Username and/or auth_token incorrect.")
                raise cherrypy.HTTPError(403, "Username and/or auth_token incorrect.")
            if "action_list" not in data_in:
                logger.error("Batch requests require an action_list.")
                raise cherrypy.HTTPError(400, "Batch requests require an action_list.")
            # Process each action in action_list
            for items in data_in["action_list"].items():
                #logger.error(action, action[action])
                # Check that each action has a command and optional arg list
                if "action" not in items[1]:
                    logger.error("Each item in action_list needs an action.")
                    raise cherrypy.HTTPError(400, "Each item in action_list needs an action.")
                action = items[1]["action"]
                if "args" not in items[1]:
                    args = None
                elif "args" == {}:
                    args = None
                else:
                    args = items[1]["args"]
                if action in prohibited_actions:
                    logger.error("Action %s prohibited" % action)
                    raise cherrypy.HTTPError(405, "Action %s prohibited" % action)
                # Try to get the function from pyredstone module. Then pass the arg list.
                try:
                    methodToCall = getattr(pyredstone, action)
                    if args is None:
                        result = methodToCall()
                    else:
                        result = methodToCall(**args)
                except AttributeError as e:
                    logger.error("Action %s not found." % action)
                    raise cherrypy.HTTPError(404, "Action %s not found." % action)
                
                response[action] = result
            logger.debug(response)
            return response
        else:
            if pyredstone.status:
                return "Server is running."
            else:
                return "Server is not running."
    index.exposed = True
    batch.exposed = True

if __name__ == "__main__":
	print "start"
	logger.info("Starting server on 0.0.0.0:7777")

	# daemonize
	d = Daemonizer(cherrypy.engine)
	d.subscribe()
	PIDFile(cherrypy.engine, '/var/run/pyredstone/server.pid').subscribe()
	cherrypy.config.update({"server.socket_host": "0.0.0.0",
        	                "server.socket_port": 7777,
                	       })
	cherrypy.quickstart(Root())
