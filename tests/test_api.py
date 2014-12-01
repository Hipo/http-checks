import unittest
from multiprocessing import Process
from httpchecks.httpcheck import server
import requests
import time
import json

class TestApiFunctions(unittest.TestCase):

    def setUp(self):
        self.server_process = Process(target=server)
        self.server_process.start()
        time.sleep(0.2)

    def test_choice(self):
        # see if our server is up and running
        r = requests.get('http://localhost:8091/hello')
        o = json.loads(r.content)
        assert o['result']

    def tearDown(self):
        self.server_process.terminate()

if __name__ == '__main__':
    unittest.main()