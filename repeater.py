import urllib2
import json

class Repeater():
    """ Repeater is a class for connecting to a remote pyredstone server instance. """
    headers = {}

    def __init__(self, server_url, username):
        if server_url is None:
            return SyntaxError('server_url cannot be blank.')
        if username is None:
            return SyntaxError('username cannot be blank.')
        self.headers['Content-Type'] = 'application/json'
        self.server_url = server_url
        self.username = username
    def get(self, action, args=None):
        if args is None:
            args = {}
        jdata = json.dumps({"action": action, "username": self.username, "auth_token": "", "args": args})
        req = urllib2.Request(self.server_url, jdata, self.headers)
        f = urllib2.urlopen(req)
        j = json.loads(f.read())
        return j['result']
