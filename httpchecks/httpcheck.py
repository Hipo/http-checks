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

log = logging.getLogger(__name__)

def send_metric_to_carbon(metric_name, value, graphite_host, graphite_port, ts=None):
    if not ts:
        ts = int(time.time())
    message = '%s %s %d\n' % (metric_name, value, int(ts))
    log.info("sending to graphite %s", message)
    sock = socket.socket()
    sock.connect((graphite_host, graphite_port))
    sock.sendall(message)
    sock.close()

# Monkey-patch.
gmonkey.patch_all(thread=False, select=False)

from requests import Session

class AsyncRequest(object):
    """ Asynchronous request.

    Accept same parameters as ``Session.request`` and some additional:

    :param session: Session which will do request
    :param callback: Callback called on response.
                     Same as passing ``hooks={'response': callback}``
    """
    def __init__(self, method, url, **kwargs):
        #: Request method
        self.method = method
        #: URL to request
        self.url = url
        #: Associated ``Session``
        self.session = kwargs.pop('session', None)
        if self.session is None:
            self.session = Session()

        callback = kwargs.pop('callback', None)
        if callback:
            kwargs['hooks'] = {'response': callback}

        #: The rest arguments for ``Session.request``
        self.kwargs = kwargs
        #: Resulting ``Response``
        self.response = None
        self.error = None
        self.name = None
        self.waiting_status_code = None
        self.check_text = self.check_html = None

    def send(self, **kwargs):
        """
        Prepares request based on parameter passed to constructor and optional ``kwargs```.
        Then sends request and saves response to :attr:`response`

        :returns: ``Response``
        """
        merged_kwargs = {}
        merged_kwargs.update(self.kwargs)
        merged_kwargs.update(kwargs)
        try:
            self.response = self.session.request(self.method,
                                              self.url, **merged_kwargs)
        except Exception as e:
            self.response = None
            self.error = e
            log.exception("[%s] gave exception" % self.url)
            return
        return self.response


def send(r, pool=None, stream=False):
    """Sends the request object using the specified pool. If a pool isn't
    specified this method blocks. Pools are useful because you can specify size
    and can hence limit concurrency."""
    if pool != None:
        return pool.spawn(r.send, stream=stream)

    return gevent.spawn(r.send, stream=stream)

def map(requests, stream=False, size=None):
    """Concurrently converts a list of Requests to Responses.

    :param requests: a collection of Request objects.
    :param stream: If True, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. If None, no throttling occurs.
    """

    requests = list(requests)

    pool = Pool(size) if size else None
    jobs = [send(r, pool, stream=stream) for r in requests]
    gevent.joinall(jobs)
    return [r for r in requests]


def check_html(req):
    if not req.check_html:
        return True

    soup = BeautifulSoup(req.response.content)
    for html_check in req.check_html:
        for selector, v in html_check.iteritems():
            elements = soup.select(selector)
            if not elements:
                log.debug('[%s] couldn\'t find any elements matching %s', req.url, selector)
                return False
            for el in elements:
                log.debug('[%s] checking element %s', req.url, el)
                if v.startswith('~'):
                    reg_exp = v.split('~/')[1][:-1]
                    log.debug('[%s] checking with reqexp ~/%s/', req.url, reg_exp)
                    if not re.match(reg_exp, el.get_text()):
                        log.debug('[%s] checking with reqexp %s failed', req.url, reg_exp)
                        return False
                    log.debug('[%s] checking with reqexp %s passed', req.url, reg_exp)
                else:
                    if not el.get_text() == v:
                        log.debug('[%s] failed because el text doesnt match %s', req.url, v)
                        return False
    return True

def check_text(req):
    if not req.check_text:
        return True
    return req.check_text in req.response.content

def check_status_code(req):
    log.debug("[%s] checking status code waiting: %s actual: %s", req.url, req.waiting_status_code, req.response.status_code)
    return req.response.status_code in req.waiting_status_code

def check_response(req):
    return req.response

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='config file', dest='config_file', default='check.yml')
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
        r = AsyncRequest(
                method=urlconf.get('method', 'GET'),
                timeout=urlconf.get('timeout', 5.0),
                url=urlconf['url'],
                allow_redirects=urlconf.get('allow_redirects', True),
                headers=urlconf.get('headers', None)
            )
        r.name = k
        r.waiting_status_code = urlconf.get('status_code', None)
        if not r.waiting_status_code:
            r.waiting_status_code = [200]

        r.check_text = urlconf.get('text', None)
        r.check_html = urlconf.get('html', None)
        rs.append(r)

    checks = [
        check_response,
        check_status_code,
        check_text,
        check_html
    ]

    reqs = map(rs, size=config.get('pool_size', 10))
    exit_code = 0

    for req in reqs:
        elapsed = -1

        failed = False
        for check in checks:
            if not check(req):
                failed = True
                log.critical('[%s] FAILED check - %s', req.url, check)
                break

        if not failed:
            elapsed = req.response.elapsed.total_seconds()
        else:
            exit_code = 2

        if not config['settings'].get('dry_run', False) \
            and graphite_host and graphite_port:
            send_metric_to_carbon('http_check.%s' % req.name,
                              elapsed,
                              graphite_host=graphite_host,
                              graphite_port=graphite_port)
        else:
            log.info("[%s] completed in %s", req.name, elapsed)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
