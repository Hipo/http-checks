try:
    import gevent
    from gevent import monkey as gmonkey
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError('Gevent is required.')

import logging

log = logging.getLogger(__name__)

from requests import Session
from checks import check_html, check_response, check_status_code, check_text


checks = [
    check_response,
    check_status_code,
    check_text,
    check_html
]


class SessionedChecks(object):
    """
    this is just a container for tests with sessions
    """
    def __init__(self, name, finish_callback, options=None):
        self.name = name
        self.session = Session()
        self.steps = []
        self.step_num = 0
        self.finished = finish_callback
        self.options = options or {}

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
                    self.finished(False, self)
                    return
            self.run(next_req)
        else:
            self.finished(True, self)

    def run(self, rs=None):

        if not rs:
            rs = self.next()

        p = gevent.spawn(rs.send, stream=None)
        p.request = rs
        p.link(self.run_cb)
