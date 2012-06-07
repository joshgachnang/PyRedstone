import urllib2
import urllib
import json
from repeater import Repeater

def test_json():
    repeater = Repeater('http://nang.kicks-ass.net:7777', 'josh')
    print repeater.get('get_banned', {})

def test_json_batch():
    repeater = Repeater('http://nang.kicks-ass.net:7777', 'josh')
    print repeater.batch([('get_players', {}), ('get_banned', {"player_type": "player"})])
    repeater = Repeater('http://nang.kicks-ass.net:7777', 'josh')
    print repeater.batch([('get_players', {}), ('get_banned', {"player_type": "player"})])
    repeater = Repeater('http://nang.kicks-ass.net:7777', 'josh')
    print repeater.batch([('get_players', {}), ('get_banned', {"player_type": "player"})])

if __name__ == '__main__':
    #test_json()
    #print "Testing json batch"
    test_json_batch()