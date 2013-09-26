import json

SUPPORTED_COLORS = [
    '000000',
    'FF0000',
    '00FF00',
    '0000FF',
    'FFFF00',
    '00FFFF',
    'FF00FF',
    'FFFFFF',
]

MIN_COLORS_ALLOWED = 1
MAX_COLORS_ALLOWED = 10
MIN_DURATION_MS = 0
MAX_DURATION_MS = 4000  # 4 seconds

_EXPECTED_KEYS = [
    'display_duration_ms',
    'fadeout_duration_ms',
    'colors',
]


def parse_config(config):
    """Parses and returns the given JSON string as a dict.

    This function also validates the argument and raises a ValueError
    if there are any problems.
    """
    config = json.loads(config)

    # Ensures all expected keys are there.
    for key in _EXPECTED_KEYS:
        if key not in config:
            raise ValueError('Expected key missing: {0}'.format(key))

    # Validates the duration values.
    for key in ['display_duration_ms', 'fadeout_duration_ms']:
        duration = config[key]
        if not isinstance(duration, int):
            raise ValueError('{0} must be an int.'.format(key))

        if duration not in xrange(MIN_DURATION_MS, MAX_DURATION_MS + 1):
            raise ValueError(
                '{key} must be in the range [{min}, {max}]. Received: {val}'
                .format(
                    key=repr(key),
                    min=_MIN_DURATION_MS,
                    max=_MAX_DURATION_MS,
                    val=duration))

    # Validates the colors.
    colors = config['colors']
    if len(colors) not in xrange(MIN_COLORS_ALLOWED,
                                 MAX_COLORS_ALLOWED + 1):
        raise ValueError(
            'Number of colors must be in range [{min}, {max}]. '
            'Received: {num_colors}'.format(
                min=MIN_COLORS_ALLOWED,
                max=MAX_COLORS_ALLOWED,
                num_colors=len(colors)))

    for color in colors:
        if color not in SUPPORTED_COLORS:
            raise ValueError(
                'Unrecognized color: {0}. Must be one of {1}.'.format(
                    color, repr(SUPPORTED_COLORS)))

    return config
