import unittest
from multiprocessing import Process
from httpchecks.httpcheck import server
import requests
import time
import json
import yaml

base_url = 'http://localhost:8091'

class TestApiFunctions(unittest.TestCase):

    def setUp(self):
        self.server_process = Process(target=server)
        self.server_process.start()
        time.sleep(0.2)

    def test_choice(self):
        # see if our server is up and running
        r = requests.get('%s/hello' % base_url)
        o = json.loads(r.content)
        assert o['result']

        data = """
google:
    url: http://www.google.com/
    # dont follow redirects
    allow_redirects: False
    # check if status code is 301 or 302
    status_code: [301, 302]
        """
        yaml.load(data)
        r = requests.post('%s/check' % base_url,
                          headers={'content-type': 'application/json'},
                          data=json.dumps(yaml.load(data)))

        print r.content
        time.sleep(4)

    def tearDown(self):
        self.server_process.terminate()

if __name__ == '__main__':
    unittest.main()