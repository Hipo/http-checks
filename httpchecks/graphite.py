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

def send_metric_to_carbon(metric_name, value, graphite_host, graphite_port, ts=None):
    if not ts:
        ts = int(time.time())
    message = '%s %s %d\n' % (metric_name, value, int(ts))
    log.info("sending to graphite %s", message)
    sock = socket.socket()
    sock.connect((graphite_host, graphite_port))
    sock.sendall(message)
    sock.close()
