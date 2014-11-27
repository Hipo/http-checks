from bs4 import BeautifulSoup
import logging
import re

log = logging.getLogger(__name__)

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
    log.debug("[%s] response %s ", req.url, req.response.content)
    return req.check_text in req.response.content

def check_status_code(req):
    log.debug("[%s] checking status code waiting: %s actual: %s", req.url, req.waiting_status_code, req.response.status_code)
    return req.response.status_code in req.waiting_status_code

def check_response(req):
    log.debug("[%s] response %s ", req.url, req.response.content)
    return req.response