import unittest
import pyredstone.pyredstone as pyredstone
import time

class TestServerStatus(unittest.TestCase):
    def setUp(self):
        self.pr = pyredstone.RedstoneServer('/home/josh/minecraft/pyredstone.cfg')

    def tearDown(self):
        pass

    def test_start_stop(self):
        print "Testing start/stop"
        self.pr.server_stop(msg='Going down for testing')
        print "Waiting for server to start up again."
        while self.pr.status():
            time.sleep(1)
        self.pr.server_start()
        print "Starting twice"
        self.pr.server_start()
        self.pr.server_stop(msg='Going down for testing')
        print "Waiting for server to start up again."
        while self.pr.status():
            time.sleep(1)
        print "Stopping twice"
        self.pr.server_stop(msg='Going down for testing')
        print "Waiting for server to start up again."
        while self.pr.status():
            time.sleep(1)

    def test_start_stop_quick(self):
        self.pr.server_start()
        self.pr.server_stop(quick=True, msg='Going down for testing')
        print "Waiting for server to start up again."
        while self.pr.status():
            time.sleep(1)

    def test_restart(self):
        self.pr.server_stop(msg='Going down for testing')
        print "Waiting for server to start up again."
        while self.pr.status():
            time.sleep(1)
        self.pr.server_restart(msg='Going down for testing')
        self.pr.server_restart(msg='Going down for testing')
        self.pr.server_restart(quick=True)

    def test_status(self):
        self.pr.server_stop(quick=True, msg='Going down for testing')
        self.assertFalse(self.pr.status())
        self.pr.server_start()
        self.assertTrue(self.pr.status())

if __name__ == '__main__':
    unittest.main()
