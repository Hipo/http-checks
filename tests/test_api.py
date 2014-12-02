import unittest
from multiprocessing import Process
from httpchecks.httpcheck import server
import requests
import time
import json
import yaml

base_url = 'http://localhost:8091'

from flask import Flask, session, redirect, url_for, escape, request

app = Flask(__name__)

@app.route('/result', methods=['POST'])
def result():
    print "================================="
    print "hit back result", request.json
    print "================================="
    return "last"

def run_collector():
    app.run(port=9991, debug=False)

class TestApiFunctions(unittest.TestCase):

    def setUp(self):
        self.server_process = Process(target=server)
        self.server_process.start()
        self.collector_process = Process(target=run_collector)
        self.collector_process.start()
        time.sleep(0.2)

    def test_choice(self):
        # see if our server is up and running
        r = requests.get('%s/hello' % base_url)
        o = json.loads(r.content)
        assert o['result']
        data = """
google:
    url: http://localhost:5002/sleep/1
    timeout: 20
        """
        payload = yaml.load(data)
        payload['options'] = dict(
            callback_url='http://localhost:9991/result'
        )
        r = requests.post('%s/check' % base_url,
                          headers={'content-type': 'application/json'},
                          data=json.dumps(payload))

        data = """
test-foo:
    -
        url: http://localhost:5002/sleep/1
        timeout: 20
    -
        url: http://localhost:5000/?first=1
    -
        url: http://localhost:5000/last
        """
        payload = yaml.load(data)
        payload['options'] = dict(
            callback_url='http://localhost:9991/result'
        )
        r = requests.post('%s/check' % base_url,
                          headers={'content-type': 'application/json'},
                          data=json.dumps(payload))

        data = """
google:
    url: http://www.google.com/
    # dont follow redirects
    allow_redirects: False
    # check if status code is 301 or 302
    status_code: [301, 302]
        """
        payload = yaml.load(data)
        payload['options'] = dict(
            callback_url='http://localhost:9991/result'
        )
        r = requests.post('%s/check' % base_url,
                          headers={'content-type': 'application/json'},
                          data=json.dumps(payload))

        print r.content
        time.sleep(10)

    def tearDown(self):
        self.server_process.terminate()
        self.collector_process.terminate()

if __name__ == '__main__':
    unittest.main()