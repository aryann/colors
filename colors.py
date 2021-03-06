"""A CRUD minus the D for dealing with colors for a special use-case."""

__author__ = 'Aryan Naraghi (aryan.naraghi@gmail.com)'

import common
import httplib
import json
import logging
import os
import time
import webapp2

from google.appengine.ext import ndb
from google.appengine.ext.webapp import template


_HANGING_GET_DURATION_SEC = 25


class ColorConfig(ndb.Model):
    insert_time = ndb.DateTimeProperty(auto_now=True)
    user_agent = ndb.StringProperty()
    ip = ndb.StringProperty()

    colors = ndb.StringProperty(repeated=True, choices=common.SUPPORTED_COLORS)
    display_duration_ms = ndb.IntegerProperty(required=True)
    fadeout_duration_ms = ndb.IntegerProperty(required=True)


    @staticmethod
    def default():
        return ColorConfig(
            display_duration_ms=1000,
            fadeout_duration_ms=1000,
            colors=['FFFFFF', 'FF00FF'])

    def to_dict(self):
        return {
            'colors': self.colors,
            'display_duration_ms': self.display_duration_ms,
            'fadeout_duration_ms': self.fadeout_duration_ms,
        }

    def __eq__(self, other):
        if other is None:
            return False
        return (self.colors == other.colors and
                self.display_duration_ms == other.display_duration_ms and
                self.fadeout_duration_ms == other.fadeout_duration_ms)

    def __ne__(self, other):
        return not self.__eq__(other)


class ColorHandler(webapp2.RequestHandler):
    """Handler for setting and viewing the colors."""

    def get_latest(self):
        """Returns the latest color record or None."""
        query = ColorConfig.query().order(-ColorConfig.insert_time)
        results = query.fetch(1)
        if results:
            return results[0]
        else:
            return None

    def get(self):
        """Handles requests to get the color configurations as JSON.

        Clients can pass in hang=1 as a GET parameter to cause the
        request to hang until configs have changed.
        """
        current = self.get_latest()
        if not current:
            current = ColorConfig.default()
            current.put()
        new = current

        if self.request.get('hang') == '1':
            start = time.time()
            while True:
                new = self.get_latest()
                if new != current:
                    break

                time.sleep(1)
                if time.time() - start > _HANGING_GET_DURATION_SEC:
                    break

        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(new.to_dict()))
        self.response.write('\n')

    def post(self):
        """Handles requests to change the color configuration."""
        logging.info('Received POST request: %s', self.request.body)

        try:
            payload = common.parse_config(self.request.body)
        except ValueError as e:
            self.response.headers['Content-Type'] = 'application/text'
            self.response.write(e.message)
            self.response.set_status(httplib.BAD_REQUEST)
            return

        config = ColorConfig(
            display_duration_ms=payload['display_duration_ms'],
            fadeout_duration_ms=payload['fadeout_duration_ms'],
            colors=payload['colors'],
            user_agent=self.request.user_agent,
            ip=self.request.remote_addr)
        config.put()

        self.response.set_status(httplib.OK)


class MainPage(webapp2.RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        template_vals = {
            'colors_min': common.MIN_COLORS_ALLOWED,
            'colors_max': common.MAX_COLORS_ALLOWED,
            'duration_min': common.MIN_DURATION_MS,
            'duration_max': common.MAX_DURATION_MS,
            'supported_colors': common.SUPPORTED_COLORS}
        self.response.write(template.render(path, template_vals))


app = webapp2.WSGIApplication([
        ('/', MainPage),
        ('/colors', ColorHandler),
        ])
