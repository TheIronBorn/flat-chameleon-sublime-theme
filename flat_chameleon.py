'''
Licensed under MIT
Copyright (c) 2015 r3a1ay <https://github.com/r3a1ay>
'''

import re
import sublime
import sublime_plugin
import sys
from .lib.rgba import RGBA
from .lib.resource import resource
from plistlib import readPlistFromBytes

msg_er_parser = 'Parser error: %s'
msg_er_scheme = 'Color scheme "%s" cannot be parsed'
msg_er_var = 'Unknown var: %s'

package = 'Flat Chameleon'

re_var_decl = re.compile('//\s*(\w+)\s*=\s*(.*)')
re_var = re.compile('\$(\w+)')
re_value = re.compile(
    '('
    '(\@([\w.]+))|'
    '(\$(\w+))|'
    '(\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\])'
    ')'
    ',?\s*([-+]?\d+)?\s*,?\s*([-+]?\d+)?\s*,?\s*([-+]?\d+)?')
re_ws = re.compile('[ \t]+')


class Chameleonize(sublime_plugin.TextCommand):

    def add_error(self, msg, msg_params=None):
        if msg_params is None:
            msg_params = ()
        msg = msg % msg_params
        if msg not in self.errors:
            self.errors.append(msg)
            print('FCT: ' + msg)

    def parse(self, value):
        mo = re_value.match(value)
        if mo is None:
            return value

        dh, ds, dl = 0, 0, 0

        if mo.group(3):
            if mo.group(3) in self.color_map:
                hex_color = self.color_map[mo.group(3)]
                clr = RGBA(hex_color)
            else:
                clr = self.fgcolor
        elif mo.group(5):
            if mo.group(5) in self.var_map:
                c = self.var_map[mo.group(5)].split(',')
                clr = RGBA()
                clr.r = int(c[0].strip())
                clr.g = int(c[1].strip())
                clr.b = int(c[2].strip())
            else:
                self.add_error(msg_er_var, mo.group(5))
                clr = RGBA('#FF00FF')
        elif mo.group(6):
            clr = RGBA()
            clr.r = int(mo.group(7))
            clr.g = int(mo.group(8))
            clr.b = int(mo.group(9))
        else:
            self.add_error(msg_er_parser, mo.group(0))
            clr = RGBA('#FF00FF')

        if mo.group(10):
            dh = int(mo.group(10))
        if mo.group(11):
            ds = int(mo.group(11))
        if mo.group(12):
            dl = int(mo.group(12))

        h, l, s = clr.tohls()
        h += dh
        l += -dl / 255 if self.is_dark else dl / 255
        if s > 0:
            s += -ds / 255 if self.is_dark else ds / 255
        clr.fromhls(h, max(0, min(l, 1)), max(0, min(s, 1)))

        if clr.a < 255:
            a = clr.a / 255
            clr.r = int(self.bgcolor.r + (clr.r - self.bgcolor.r) * a)
            clr.g = int(self.bgcolor.g + (clr.g - self.bgcolor.g) * a)
            clr.b = int(self.bgcolor.b + (clr.b - self.bgcolor.b) * a)

        return '%d, %d, %d' % (clr.r, clr.g, clr.b)

    def run(self, edit):
        settings = sublime.load_settings('Preferences.sublime-settings')
        if settings.get('theme') != 'Flat Chameleon.sublime-theme':
            return

        self.var_map = {}
        self.color_map = FCColorSchemeListener.inst.get_color_map(self.view)
        self.color_scheme = FCColorSchemeListener.inst.color_scheme
        self.errors = []

        if self.color_map is not None:
            self.fgcolor = RGBA(self.color_map['foreground'])
            self.bgcolor = RGBA(self.color_map['background'])
            self.is_dark = self.bgcolor.tohls()[1] < 0.5

            template = resource(package, 'Flat Chameleon.sublime-theme.templ')
            if template:
                for mo in re_var_decl.finditer(template):
                    self.var_map[mo.group(1)] = self.parse(mo.group(2))

                def repl(mo):
                    if mo.group(1) in self.var_map:
                        return self.var_map[mo.group(1)]
                    self.add_error(msg_er_var, mo.group(0))

                template = re_var.sub(repl, template)

                if not self.errors:
                    resource(package, 'Flat Chameleon.sublime-theme', template)
                    settings = sublime.load_settings('Widget.sublime-settings')
                    settings.set('color_scheme', self.color_scheme)
                    sublime.save_settings('Widget.sublime-settings')
        else:
            self.add_error(msg_er_scheme, self.color_scheme)

        if self.errors:
            sublime.status_message('; '.join(self.errors))


class FCColorSchemeListener(sublime_plugin.EventListener):

    inst = None

    def __init__(self):
        FCColorSchemeListener.inst = self
        self.color_scheme = None
        self.color_map = None
        self.init()

    def init(self):
        if sublime.active_window() is None or \
                sublime.active_window().active_view() is None:
            sublime.set_timeout(self.init, 200)
            return

        self.settings = sublime.load_settings('Preferences.sublime-settings')

        if self.settings.get('theme') == 'Flat Chameleon.sublime-theme':
            self.settings.add_on_change(
                'color_scheme', lambda: self.parse_scheme())
            self.parse_scheme()

    def get_color_map(self, view):
        if self.color_map is None:
            self.parse_scheme()

        return self.color_map

    def parse_scheme(self):
        if sublime is None:
            return
        self.settings = sublime.load_settings('Preferences.sublime-settings')
        color_scheme = self.settings.get(
            'color_scheme',
            'Packages/Color Scheme - Default/Monokai.tmTheme')

        settings = sublime.load_settings('Widget.sublime-settings')
        update_theme = settings.get('color_scheme') != color_scheme

        if self.color_scheme == color_scheme and self.color_map is not None:
            return

        self.color_scheme = color_scheme
        self.color_map = None

        try:
            res = sublime.load_binary_resource(self.color_scheme)
            plist = readPlistFromBytes(res)
        except:
            print('FCT: ' + sys.exc_info()[0])
            return

        def safe_update(fr, to, scope=''):
            for k in fr.keys():
                if scope:
                    scopes = scope.split()
                    to_k = ''
                    while scopes:
                        scopes.append(k)
                        to_k = '.'.join(scopes)
                        if to_k not in to:
                            to[to_k] = fr[k]
                        scopes.pop()
                        scopes.pop()
                else:
                    if k not in to:
                        to[k] = fr[k]

        self.color_map = {}
        for d in plist.settings:
            if 'settings' not in d:
                continue
            settings = d['settings']
            if 'scope' not in d:
                safe_update(settings, self.color_map)
            else:
                scope = re_ws.sub(d['scope'], ' ')
                scopes = [sc.strip() for sc in scope.split(',')]
                if 'text' in scopes or 'source' in scopes:
                    self.color_map.update(settings)
                else:
                    for scope in scopes:
                        safe_update(settings, self.color_map, scope)

        if update_theme:
            sublime.active_window().run_command('chameleonize')
