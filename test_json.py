import urllib2
import urllib
import json
from repeater import Repeater

def test_json():
    repeater = Repeater('http://minecraft:7777', 'josh')
    print repeater.send('get_players', {})
    
if __name__ == '__main__':
    test_json()