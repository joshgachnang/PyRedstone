import urllib2
import json
import urlparse


class RepeaterEmptyReponse(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RepeaterInvalidReponse(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Repeater():
    """ Repeater is a class for connecting to a remote pyredstone server instance. """
    headers = {}

    def __init__(self, server_url, username):
        if server_url is None:
            return SyntaxError('server_url cannot be blank.')
        if username is None:
            return SyntaxError('username cannot be blank.')
        self.headers['Content-Type'] = 'application/json'
        self.headers['Accept'] = 'text/plain'
        self.server_url = server_url
        self.username = username
        self.auth_token = ""

    def get(self, action, args=None):
        if args is None:
            args = {}
        jdata = json.dumps({"action": action, "username": self.username, "auth_token": self.auth_token, "args": args})
        response = self.send_request(jdata)
        print response
        if "result" in response:
            return response["result"]
        else:
            if response is None:
                raise RepeaterEmptyResponse("Empty response received from the server")
            else:
                raise RepeaterInvalidReponse("Invalid response received from the server")

    def send_request(self, jdata, url=""):
        """ Given a JSON dict, send it to the server """
        url = urlparse.urljoin(self.server_url, url)
        print "Sending: ", url, ",", jdata, ",", self.headers
        req = urllib2.Request(url, jdata, self.headers)
        f = urllib2.urlopen(req)
        j = json.loads(f.read())
        return j

    def batch(self, get_list):
        """ Takes a list of tuples as get_list. The tuples should be of the form ("command", {arglist})
        The JSON will look like: {"username": username, "auth_token": auth_token, "command": {"command", {arglist}}}
        """
        print "starting batch"
        jdata = {}
        jdata["username"] = self.username
        jdata["auth_token"] = self.auth_token
        jdata["action_list"] = {}

        for item in get_list:
            action = item[0]
            args = item[1]
            jdata["action_list"][action] = {"action": action, "args": args}

        #print "Jdata is ", json.dumps(jdata)

        #print json.loads(json.dumps(jdata))

        response = self.send_request(json.dumps(jdata), "batch")
        if response is None:
            raise RepeaterEmptyResponse("Empty response received from the server")
        else:
            return response
