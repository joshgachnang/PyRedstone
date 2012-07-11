import unittest
try:
    import pyredstone
except ImportError as e:
    import pyredstone.pyredstone as pyredstone
class TestServerStatus(unittest.TestCase):
    def setUp(self):
        self.pr = pyredstone.RedstoneServer('/home/josh/minecraft/pyredstone.cfg')

    def tearDown(self):
        pass

    def test_start_stop(self):
        print "Testing start/stop"
        self.pr.server_stop()
        self.pr.server_start()
        print "Starting twice"
        self.pr.server_start()
        self.pr.server_stop()
        print "Stopping twice"
        self.pr.server_stop()

    def test_start_stop_quick(self):
        self.pr.server_start()
        self.pr.server_stop(quick=True)

    def test_restart(self):
        self.pr.server_stop()
        self.pr.server_restart()
        self.pr.server_restart()
        self.pr.server_restart(quick=True)

    def test_status(self):
        self.pr.server_stop(quick=True)
        self.assertFalse(self.pr.status())
        self.pr.server_start()
        self.assertTrue(self.pr.status())

if __name__ == '__main__':
    unittest.main()
