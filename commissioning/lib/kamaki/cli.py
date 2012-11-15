#!/usr/bin/env python

from kamaki.cli.commands import _command_init
from kamaki.cli import command
from kamaki.cli.errors import CLIError

class cli_generator(object):

    api_spec = None
    appname = None
    plugin = None
    add_context = False

    def __init__(self):
        self.api_spec = self.plugin.api_spec
        self.appname = self.plugin.appname

    def generate_all(self):
        for f in self.api_spec.call_names():
            c = self.mkClass(f)
            command()(c)

    def mkClass(self, method):
        class C(_command_init):

            __doc__ = self.api_spec.get_doc(method)

            def init(this):
                this.token = (this.config.get(self.appname, 'token') or
                              this.config.get('global', 'token'))
                this.base_url = (this.config.get(self.appname, 'url') or
                                 this.config.get('global', 'url'))
                this.client = self.plugin(this.base_url, this.token)

            def call(this, method, args):
                ctx = '=null ' if self.add_context else ''
                arglist = '[' + ctx + ' '.join(args) + ']'
                argdict = self.api_spec.parse(method, arglist)
                f = getattr(this.client, method)
                return f(**argdict)

            def main(this, *args):
                this.init()
                try:
                    r = this.call(method, args)
                    print r
                except Exception as e:
                    raise CLIError ('%s: %s\n' % (self.appname, e))

        C.__name__ = self.appname + '_' + method
        return C
