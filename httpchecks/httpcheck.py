try:
    import gevent
    from gevent import monkey as gmonkey
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError('Gevent is required.')

import yaml
import socket
import time
import logging
import argparse
from bs4 import BeautifulSoup
import re
import sys
import json
import requests

log = logging.getLogger(__name__)

from .graphite import send_metric_to_carbon
from .notifiers import notify_by_slack

# Monkey-patch.
gmonkey.patch_all(thread=False, select=False)

from checks import check_html, check_response, check_status_code, check_text
from async_req import send, map, AsyncRequest, run_req

def get_request(k, urlconf, callback=None, session=None):
    r = AsyncRequest(
            method = urlconf.get('method', 'GET'),
            timeout = urlconf.get('timeout', 5.0),
            url = urlconf['url'],
            allow_redirects = urlconf.get('allow_redirects', True),
            headers = urlconf.get('headers', None),
            data = urlconf.get('data', None),
            session = session,
            callback = callback
        )
    r.name = k
    r.waiting_status_code = urlconf.get('status_code', None)
    if not r.waiting_status_code:
        r.waiting_status_code = [200]

    r.check_text = urlconf.get('text', None)
    r.check_html = urlconf.get('html', None)
    return r

checks = [
    check_response,
    check_status_code,
    check_text,
    check_html
]


ready = gevent.event.Event()
ready.clear()

finished_jobs = 0
sync_map = []

def finished(result):
    global exit_code, finished_jobs
    finished_jobs += 1

    if not result:
        # if any of the tests fail we fail too
        exit_code = 2

    if finished_jobs == len(sync_map):
        log.info('all waiting jobs are completed.')
        ready.set()

from requests import Session

class SessionedChecks(object):
    """
    this is just a container for tests with sessions
    """
    def __init__(self, name):
        self.name = name
        self.session = Session()
        self.steps = []
        self.step_num = 0

    def add(self, rs):
        self.steps.append(rs)

    def next(self):
        try:
            step = self.steps[self.step_num]
            self.step_num += 1
            return step
        except IndexError:
            return None

    def run_cb(self, *args, **kwargs):
        next_req = self.next()

        if next_req:
            print "next url", next_req.url
            for check in checks:
                self.result = check(args[0].request)
                if not self.result:
                    log.warn("[%s] test failed - step:%s - %s" % (self.name, self.step_num-2, self.steps[self.step_num-2].url))
                    finished(False)
                    return
            self.run(next_req)
        else:
            finished(True)

    def run(self, rs=None):

        if not rs:
            rs = self.next()

        p = gevent.spawn(rs.send, stream=None)
        p.request = rs
        p.link(self.run_cb)


exit_code = 0



from gevent.wsgi import WSGIServer
from .apiserver import app


def server():
    http_server = WSGIServer(('0.0.0.0', 8091), app)
    http_server.serve_forever()

def main():
    global exit_code

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='config file',
                        dest='config_file', default='check.yml')
    args = parser.parse_args()
    config = yaml.load(open(args.config_file))

    logging.basicConfig(level=config['settings'].get('log_level', 'DEBUG').upper())

    graphite_host = config['settings'].get('graphite_host')
    try:
        graphite_port = int(config['settings'].get('graphite_port'))
    except:
        graphite_port = None

    rs = []

    for k, urlconf in config['urls'].iteritems():
        # different sessions can run in parallel
        if isinstance(urlconf, list):
            sc = SessionedChecks(name=k)
            for c in urlconf:
                # but individual urls in session must run in sync.
                r = get_request(k, c, session=sc.session)
                sc.add(r)
            sync_map.append(sc)

        else:
            # these can run in parallel, because they dont need to have a defined flow
            r = get_request(k, urlconf)
            rs.append(r)

    for sm in sync_map:
        sm.run()

    reqs = map(rs, size=config.get('pool_size', 10))

    for req in reqs:
        success = run_req(req, config, graphite_host, graphite_port)
        if not success:
            exit_code = 2

    if sync_map:
        ready.wait()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
