import unittest
import pyredstone

class TestServerStatus(unittest.TestCase):
    def setUp(self):
        self.pr = pyredstone.RedstoneServer('/home/josh/minecraft/pyredstone.cfg')

    def tearDown(self):
        pass

    def test_start(self):
        print 'woot.'

    def test_start_again(self):
        pass

    def test_stop(self):
        pass

    def test_stop_again(self):
        pass

    def test_restart(self):
        pass

    def test_status(self):
        pass

if __name__ == '__main__':
    unittest.main()