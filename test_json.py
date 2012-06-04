import urllib2
import urllib
import json
def test_json():
    headers = {}
    headers['Content-Type'] = 'application/json'
    jdata = json.dumps({"action": "get_players", "username": "josh", "auth_token": "", "args": {}})
    req = urllib2.Request('http://minecraft:7777', jdata, {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    j = json.loads(f.read())
    print j['result']

if __name__ == '__main__':
    test_json()