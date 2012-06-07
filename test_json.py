import urllib2
import urllib
import json
from repeater import Repeater

def test_json():
    repeater = Repeater('http://minecraft:7777', 'josh')
    print repeater.get('get_players', {})

def test_json_batch():
    repeater = Repeater('http://minecraft:7777', 'josh')
    print repeater.batch([('get_players', {}), ('get_banned', {"player_type": "ip"})])

if __name__ == '__main__':
    test_json()