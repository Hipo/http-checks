from setuptools import setup

setup(
    name='http-checks',
    version='0.2.1',
    author='ybrs',
    description='http-checks is an application that can test a couple of hundred urls in seconds',
    long_description=__doc__,
    packages=['httpchecks'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['pyyaml', 'requests', 'gevent', 'beautifulsoup4', 'jsonpath_rw'],
    url='https://github.com/Hipo/http-checks',
    entry_points = {
        'console_scripts': [
            'http-checks = httpchecks.httpcheck:main',
        ],
    }
)
