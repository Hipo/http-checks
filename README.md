http-checks
-------------------
http-checks is a simple url checker, that sends results to graphite - or just print to stdout.

It uses gevent, although our main aim is not on performance, it can check a couple of hundred urls in few seconds.

Installation
-------------------
```
pip install http-checks
```

Configuration
-------------------
configuration is a single yml file

```yaml
settings:
    graphite_server: http://localhost
    graphite_port: 2003
    pool_size: 50
    # if you dont want to send to graphite.
    dry_run: True
    log_level: INFO

    # alert to slack if you want to
    slack:
        channel: '#alerts'
        username: 'alertus'
        icon_emoji: ':warning:'
        url: 'https://XXX.slack.com/services/hooks/incoming-webhook?token=12233443'


urls:
    google:
        url: http://www.google.com/
        # dont follow redirects
        allow_redirects: False
        # check if status code is 301 or 302
        status_code: [301, 302]

    org.python:
        url: http://www.python.org/

        # this will check this text exists in html source
        text: Python is a programming language that lets you work quickly

        # some html checks
        html:
            # this will check if title element == Welcome to Python.org
            - title: Welcome to Python.org
            # or write a reqular expression, surround your reg. exp. with ~/ /
            - title: ~/.*Python.*/
            # we pass selector directly to (beatifulsoup.select)[http://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors]
            # so you do this, suppose there is some html like this
            #
            # <h1 class="site-headline">
            #        <a href="/"><img class="python-logo" src="/static/img/python-logo.png" alt="python&trade;"></a>
            # </h1>
            #
            # you can check if element exists with a css selector and an empty reg. exp.
            - h1.site-headline > a > img.python-logo: ~//

    # you can also use more than one url, for testing scenerios.
    # these will run synchronously, meaning, it will first request the first
    # url, then the second, then the third etc.
    #
    # scenerio tests runs in parallel, so you can check login
    # and the create new user scenerios at the same time.
    #
    # a scenerio test, uses the same session in individual urls. but doesn't share
    # the session in other scenerios.
    test-login:
        -
            url: http://localhost:5000/?first=1

        # check home page
        -
            url: http://localhost:5000/

        # now get login
        -
            url: http://localhost:5000/login

        # post to login
        -
            url: http://localhost:5000/login
            method: POST
            data:
                username: xyz
                password: 123
        -
            # now go back to / and see if our username is there
            url: http://localhost:5000/
            text: xyz
        -
            # now go back to / and see if our username is there
            url: http://localhost:5000/last
```

Running
------------
The best way to run it, is adding it to cron or running it via jenkins with regular intervals.

```
http-checks -c config.yml
```

then you can check if some urls fails with (graphite-alerts)[https://github.com/ybrs/graphite-alerts]

If any of the tests fails, we exit with status code 2, so you can add this to your deploy scripts, alerting systems etc easily.




