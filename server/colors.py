"""A CRUD minus the D for dealing with colors for a special use-case."""

__author__ = 'Aryan Naraghi (aryan.naraghi@gmail.com)'

import json
import logging
import os
import supported_colors
import webapp2

from google.appengine.ext import db
from google.appengine.ext.webapp import template

# We only need to store one entity--this constant defines its key.
DATA_KEY = '0'

# HTTP eror code(s)
HTTP_BAD_REQUEST = 400

# Allowed value ranges
MIN_COLORS_ALLOWED = 1
MAX_COLORS_ALLOWED = 10
MIN_DURATION_MS = 0
MAX_DURATION_MS = 15000  # 15 seconds

SCHEMA = {
    'display_duration_ms': int,
    'fadeout_duration_ms': int,
    'colors': list}


def has_valid_structure(payload, schema=SCHEMA):
    """An "okay-enough" way of verifying that the given payload
    matches the expected schema.
    """
    if (not isinstance(payload, dict) or
        len(payload) != len(schema)):
        return False
    for key, type in schema.iteritems():
        if (key not in payload or
            not isinstance(payload[key], type)):
            return False
    return True


class Data(db.Model):
    colors = db.StringListProperty()
    display_duration_ms = db.IntegerProperty()
    fadeout_duration_ms = db.IntegerProperty()

    def to_dict(self):
        return {key: getattr(self, key) for key in self.properties()}


class RequestHandler(webapp2.RequestHandler):
    """Base class for handlers."""

    def return_error(self, msg, *args, **kwargs):
        self.response.clear()
        self.response.write(msg.format(*args, **kwargs))
        if msg[-1] != '\n':
            self.response.write('\n')
        self.response.set_status(HTTP_BAD_REQUEST)

    def return_json(self, payload):
        self.response.clear()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(payload))
        self.response.write('\n')


class ColorHandler(RequestHandler):
    """Handler for setting and viewing the colors."""

    def get(self):
        data = Data.get_by_key_name(DATA_KEY)
        if not data:
            self.return_error('There is no color data available right now.\n')
            return

        if self.request.get('format') == 'json':
            self.return_json(data.to_dict())
        else:
            display = str(data.display_duration_ms)
            fadeout = str(data.fadeout_duration_ms)
            for color in data.colors:
                self.response.write(':'.join((color, display, fadeout)))
                self.response.write(' ')
            self.response.write('\n')

    def post(self):
        logging.info('Received POST request: %s', self.request.body)

        self.response.headers['Content-Type'] = 'text/plain'
        payload = None
        try:
            payload = json.loads(self.request.body)
        except ValueError:
            pass

        if not has_valid_structure(payload):
            self.return_error('Request was malformed.')
            return

        for key in ('display_duration_ms', 'fadeout_duration_ms'):
            duration = payload[key]
            if duration not in xrange(MIN_DURATION_MS, MAX_DURATION_MS + 1):
                self.return_error(
                    '{key} must be in the range [{min}, {max}]. Received: {val}',
                    key=key,
                    min=MIN_DURATION_MS,
                    max=MAX_DURATION_MS,
                    val=duration)
                return

        colors = payload['colors']
        if len(colors) not in xrange(MIN_COLORS_ALLOWED,
                                     MAX_COLORS_ALLOWED + 1):
            self.return_error('Received invalid number of colors: {0}',
                             len(colors))
            return

        colors = [color.upper() for color in colors]
        for color in colors:
            if color not in supported_colors.COLORS:
                self.return_error('Unrecognized color: {0}', color)
                return

        data = Data(key_name=DATA_KEY, **payload)
        data.put()


class MainPage(webapp2.RequestHandler):

    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        template_vals = {'duration_min': MIN_DURATION_MS,
                         'duration_max': MAX_DURATION_MS,
                         'supported_colors': supported_colors.COLORS}
        self.response.write(template.render(path, template_vals))


app = webapp2.WSGIApplication([
        ('/', MainPage),
        ('/colors', ColorHandler),
        ])
