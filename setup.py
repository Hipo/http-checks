from setuptools import setup

setup(
    name='http-checks',
    version='0.1.2',
    long_description=__doc__,
    packages=['httpchecks'],
    include_package_data=True,
    zip_safe=False,
    install_requires=['pyyaml', 'requests', 'gevent', 'beautifulsoup4'],

    entry_points = {
        'console_scripts': [
            'http-checks = httpchecks.httpcheck:main',
        ],
    }
)
