from __future__ import print_function
import os
import sys
import time
from pprint import pformat
from contextlib import contextmanager

from soap.context import context as _global_context


class levels():
    name = {}
levels = levels()


for i, l in enumerate(['debug', 'info', 'warning', 'error', 'off']):
    levels.__dict__[l] = i
    levels.name[i] = l


with _global_context.no_invalidate_cache():
    _global_context.logger = {
        'level': levels.warning,
        'pause_level': levels.error,
        'color': True,
        'file': None,
        '_persistent': {},
    }
    context = _global_context.logger


def set_context(**kwargs):
    with context.no_invalidate_cache():
        context.update(kwargs)


def get_context():
    return context


_colors = {
    levels.debug: '\033[100m',
    levels.info: '\033[44m',
    levels.warning: '\033[43m',
    levels.error: '\033[41m',
}
_colors_end = '\033[0m'


def header(s, l=levels.info):
    color = _colors[l] + '\033[97m '
    colors_end = ' ' + _colors_end
    if 'color' not in os.environ['TERM'] or not get_context()['color']:
        color = '['
        colors_end = ']'
    return '{color}{level:^7}{colors_end} {s}'.format(
        color=color, level=levels.name[l], colors_end=colors_end, s=s)


def format(*args):
    return ' '.join(pformat(a) if not isinstance(a, str) else a for a in args)


def log(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    if l < get_context()['level']:
        return
    f = get_context()['file'] or sys.stdout
    begin = kwargs.get('begin', '')
    end = kwargs.get('end', '')
    print(begin + header(format(*args), l), end=end, file=f)
    while l >= get_context()['pause_level']:
        r = input(
            'Continue [Return], Stack trace [t], Debugger [d], Abort [q]: ')
        if not r:
            break
        elif r == 'd':
            import ipdb
            ipdb.set_trace()
        elif r == 't':
            import traceback
            traceback.print_stack()
        elif r == 'q':
            sys.exit(-1)


def line(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    log(*args, end='\n', l=l)


def rewrite(*args, **kwargs):
    l = kwargs.get('l', levels.info)
    log(*args, end='\r', l=l)


_last_time = {}


def persistent(name, *args, **kwargs):
    now = time.time()
    if now - _last_time.get(name, 0) <= 0.25:
        return
    _last_time[name] = now

    l = kwargs.get('l', levels.info)
    prev = get_context()['_persistent'].get(name)
    curr = args + (l, )
    if prev == curr:
        return
    get_context()['_persistent'][name] = curr
    s = []
    for k, v in get_context()['_persistent'].items():
        v = list(v)
        l = v.pop()
        s.append(k + ': ' + format(*v))
    s = '; '.join(s)
    s += ' ' * (68 - len(s))
    s = s[:70]
    rewrite(s, l=l)


def unpersistent(*args):
    p = get_context()['_persistent']
    for n in args:
        if n not in p:
            continue
        del p[n]


@contextmanager
def local_context(**kwargs):
    ctx = dict(get_context())
    set_context(**kwargs)
    yield
    set_context(**ctx)


def log_level(l):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            kwargs['l'] = l
            f(*args, **kwargs)
        return wrapped
    return wrapper


def log_enable(l):
    def wrapper(f):
        def wrapped(*args, **kwargs):
            if l < get_context()['level']:
                return
            return f(*args, **kwargs)
        return wrapped
    return wrapper


def log_context(l):
    def wrapper():
        return local_context(level=l)
    return wrapper


def _init_level():
    l = levels.warning
    if '-v' in sys.argv:
        l = levels.info
    elif '-vv' in sys.argv:
        l = levels.debug
    set_context(level=l)


labels = ['debug', 'info', 'warning', 'error', 'off']
for i, l in enumerate(labels):
    locals()[l] = log_level(i)(line)
    locals()[l + '_enable'] = log_enable(i)
    locals()[l + '_context'] = log_context(i)


_init_level()
