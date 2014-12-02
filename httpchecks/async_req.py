import logging
import time
import datetime

log = logging.getLogger(__name__)

try:
    import gevent
    from gevent import monkey as gmonkey
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError('Gevent is required.')


from requests import Session

from .graphite import send_metric_to_carbon
from .notifiers import notify_by_slack


from checks import check_html, check_response, check_status_code, check_text
checks = [
    check_response,
    check_status_code,
    check_text,
    check_html
]

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
        self.started_at = None
        self.finished_at = None

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
            self.finished_at = datetime.datetime.utcnow()
        except Exception as e:
            self.response = None
            self.error = e
            self.finished_at = datetime.datetime.utcnow()
            log.exception("[%s] gave exception" % self.url)
            return
        return self.response

    def __repr__(self):
        return "<AsyncRequest %s>" % self.url

def send(r, pool=None, stream=False, callback=None):
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

def run_req(req, config, graphite_host, graphite_port):
    success = True
    elapsed = -1
    failed = False
    for check in checks:
        if not check(req):
            failed = True
            log.critical('[%s] FAILED check - %s', req.name, check.__name__)
            slack_config = config['settings'].get('slack', None)
            if slack_config:
                notify_by_slack(
                    url = slack_config['url'],
                    channel  = slack_config['channel'],
                    username  = slack_config['username'],
                    description  = '[%s] FAILED check - %s - %s' % (req.name, req.url, check.__name__),
                    icon_emoji = slack_config['icon_emoji']
                )
            break

    if not failed:
        elapsed = req.response.elapsed.total_seconds()
        req.finished_at = time.time()
    else:
        success = False
        req.finished_at = time.time()

    if not config['settings'].get('dry_run', False) \
        and graphite_host and graphite_port:
        send_metric_to_carbon('http_check.%s' % req.name,
                          elapsed,
                          graphite_host=graphite_host,
                          graphite_port=graphite_port)
    else:
        log.info("[%s] completed in %s", req.name, elapsed)

    return success


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
