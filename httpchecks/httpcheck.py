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
from async_req import send, map, AsyncRequest, run_req, get_request


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


from sessioned_check import SessionedChecks


def finished(result):
    global exit_code, finished_jobs
    finished_jobs += 1

    if not result:
        # if any of the tests fail we fail too
        exit_code = 2

    if finished_jobs == len(sync_map):
        log.info('all waiting jobs are completed.')
        ready.set()


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
            sc = SessionedChecks(name=k, finish_callback=finished)
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
