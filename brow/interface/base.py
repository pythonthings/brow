# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import logging
import codecs
from contextlib import contextmanager
import datetime
import os
import json

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, \
    WebDriverException, \
    NoSuchWindowException

from ..compat import *
from ..core import Cookies
from .. import environ


logger = logging.getLogger(__name__)


class Browser(object):

    domain = ""

    @property
    def directory(self):
        return environ.CACHE_DIR

    @property
    def body(self):
        raise NotImplementedError()

    @property
    def soup(self):
        # https://www.crummy.com/software/BeautifulSoup/
        # docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
        # bs4 codebase: http://bazaar.launchpad.net/~leonardr/beautifulsoup/bs4/files
        soup = BeautifulSoup(self.body, "html.parser")
        return soup

    @property
    def json(self):
        return json.loads(self.body)

    @property
    def url(self):
        """return the current url"""
        # http://stackoverflow.com/questions/15985339/how-do-i-get-current-url-in-selenium-webdriver-2-python
        raise NotImplementedError()
    current_url = url

    @property
    def cookies(self):
        """Return the cookies for the current domain"""
        raise NotImplementedError()

    @classmethod
    @contextmanager
    def session(cls, options=None):
        instance = None
        try:
            instance = cls(options=options)
            instance.start_session()
            yield instance

        except Exception as e:
            exc_info = sys.exc_info()
            if instance:
                instance.handle_error(e)
            else:
                logger.exception(e)
            reraise(*exc_info)

        finally:
            if instance:
                instance.stop_session()

    def __init__(self, options=None):
        self.interface = self.create_interface(options)
        self.domains = set()

    def __enter__(self):
        """Allows browser to be used with "with" keyword"""
        self.start_session()
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        """Allows browser to be used with "with" keyword"""
        self.stop_session()

    def start_session(self):
        pass
    def stop_session(self):
        return self.close()

    def close(self):
        pass

    def handle_error(self, e):
        logger.exception(e)
        return self.dump("err")

    def dump_basepath(self, prefix, directory=None):
        """put together a full path that an extension could be appended to to get
        a full path for dumping error information

        :param directory: string, a directory you would like to use, if None then 
            environ.CACHE_DIR will be used
        :returns: string, a full directory path, basically directory/basename
        """
        if not directory:
            directory = self.directory
        basename = "{}-{}-{}".format(
            prefix,
            datetime.datetime.strftime(datetime.datetime.utcnow(), "%Y%m%dT%H%M%S%fZ"),
            self.url_parts.hostname,
        )
        if self.url_parts.path:
            basename = "{}-{}".format(basename, self.url_parts.path.replace("/", "-"))

        return os.path.join(directory, basename)

    def dump(self, prefix="dump", directory=None):
        ret = []
        inter = self.interface
        try:
            basepath = self.dump_basepath(prefix, directory)
            path = "{}.html".format(basepath)
            with codecs.open(path, encoding='utf-8', mode='w+') as f:
                f.write(self.body)
            logger.debug("Dumped html to {}".format(path))
            ret.append(path)

        except AttributeError:
            pass

        except Exception as e:
            logger.warn(e, exc_info=True)

        return ret

    def _create_interface(self, options):
        raise NotImplementedError()
    def create_interface(self, options=None):
        if not options: options = {}
        return self._create_interface(options=options)

    def load(self, *args, **kwargs):
        """I'm starting to like this one the best since load/dump seems to be what
        I've settled on for lots of other objects in this module and I think it works
        you load() the contents of a url and you can dump the contents of the url using
        dump()"""
        return self.location(*args, **kwargs)
    def visit(self, *args, **kwargs):
        return self.location(*args, **kwargs)
    def _location(self, url, ignore_cookies):
        raise NotImplementedError()
    def location(self, url, ignore_cookies=False):
        """calls the selenium driver's .get() method, and will load cookies if they
        are available

        :param url: string, the full url (scheme, domain, path)
        :param ignore_cookies: boolean, if True then don't try and load cookies
        """
        logger.debug("Loading url {}".format(url))

        inter = self.interface
        self.url_start = url
        self.url_parts = urlparse.urlparse(url)
        self.domain = self.url_parts.hostname

        # if cookies have already been loaded then don't load them again but also
        # respect passed in value
        ignore_cookies = ignore_cookies or self.domain in self.domains

        ret = self._location(url, ignore_cookies)
        self.domains.add(self.domain)
        return ret

    def element(self, css_selector):
        raise NotImplementedError()

    def has_element(self, css_selector):
        raise NotImplementedError()
