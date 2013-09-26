"""A CRUD minus the D for dealing with colors for a special use-case."""

__author__ = 'Aryan Naraghi (aryan.naraghi@gmail.com)'

import hashlib
import httplib
import json
import logging
import os
import supported_colors
import webapp2
import time

from google.appengine.ext import db
from google.appengine.ext.webapp import template


_HANGING_GET_DURATION_SEC = 25

# Allowed value ranges
_MIN_COLORS_ALLOWED = 1
_MAX_COLORS_ALLOWED = 10
_MIN_DURATION_MS = 0
_MAX_DURATION_MS = 4000  # 4 seconds


_EXPECTED_KEYS = [
    'display_duration_ms',
    'fadeout_duration_ms',
    'colors',
]


class Client(db.Model):
    user_agent = db.StringProperty()
    ip = db.StringProperty()

    @staticmethod
    def get_or_create(user_agent, ip):
        h = hashlib.sha1()
        h.update(str(user_agent))
        h.update(str(ip))
        return Client.get_or_insert(
            key_name=h.hexdigest(),
            user_agent=user_agent,
            ip=ip)


class ColorConfig(db.Model):
    insert_time = db.DateTimeProperty(auto_now=True)

    colors = db.StringListProperty()
    display_duration_ms = db.IntegerProperty()
    fadeout_duration_ms = db.IntegerProperty()

    client = db.ReferenceProperty()

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
        return self.key() == other.key()

    def __ne__(self, other):
        return not self.__eq__(other)


class ColorHandler(webapp2.RequestHandler):
    """Handler for setting and viewing the colors."""

    def get_latest(self):
        """Returns the latest color record or None."""
        result = list(ColorConfig.all().order('-insert_time').run(limit=1))
        if not result:
            return None
        return result[0]

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

    def write_error(self, msg):
        """Writes the given message to self.response."""
        self.response.clear()
        self.response.write(msg)
        self.response.write('\n')
        self.response.set_status(httplib.BAD_REQUEST)

    def post(self):
        """Handles requests to change the color configuration."""
        logging.info('Received POST request: %s', self.request.body)

        payload = None
        try:
            payload = json.loads(self.request.body)
        except ValueError:
            self.return_error('Could not parse POST body as JSON.')
            return

        for key in _EXPECTED_KEYS:
            if key not in payload:
                self.return_error('Expected key missing: {0}'.format(key))
                return

        for key in ['display_duration_ms', 'fadeout_duration_ms']:
            duration = payload[key]
            if duration not in xrange(_MIN_DURATION_MS, _MAX_DURATION_MS + 1):
                self.return_error(
                    '{key} must be in the range [{min}, {max}]. Received: {val}'
                    .format(
                        key=repr(key),
                        min=_MIN_DURATION_MS,
                        max=_MAX_DURATION_MS,
                        val=duration))
                return

        colors = payload['colors']
        if len(colors) not in xrange(_MIN_COLORS_ALLOWED,
                                     _MAX_COLORS_ALLOWED + 1):
            self.return_error(
                'Number of colors must be in range [{min}, {max}]. '
                'Received: {num_colors}'.format(
                    min=_MIN_COLORS_ALLOWED,
                    max=_MAX_COLORS_ALLOWED,
                    num_colors=len(colors)))
            return

        colors = [color.upper() for color in colors]
        for color in colors:
            if color not in supported_colors.COLORS:
                self.return_error('Unrecognized color: {0}'.format(color))
                return

        client = Client.get_or_create(
            user_agent=self.request.user_agent,
            ip=self.request.remote_addr)
        client.put()
        config = ColorConfig(
            display_duration_ms=payload['display_duration_ms'],
            fadeout_duration_ms=payload['fadeout_duration_ms'],
            colors=colors,
            client=client)
        config.put()

        self.response.set_status(httplib.OK)


class MainPage(webapp2.RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        template_vals = {
            'colors_min': _MIN_COLORS_ALLOWED,
            'colors_max': _MAX_COLORS_ALLOWED,
            'duration_min': _MIN_DURATION_MS,
            'duration_max': _MAX_DURATION_MS,
            'supported_colors': supported_colors.COLORS}
        self.response.write(template.render(path, template_vals))


app = webapp2.WSGIApplication([
        ('/', MainPage),
        ('/colors', ColorHandler),
        ])
