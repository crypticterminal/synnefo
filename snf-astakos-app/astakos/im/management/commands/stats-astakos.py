# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import division
import json
import string
from optparse import make_option

from snf_django.management.commands import SynnefoCommand, CommandError
from snf_django.management.utils import pprint_table
#from astakos.im.models import AstakosUser, Resource
#from astakos.quotaholder_app.models import Holding
from astakos.admin import stats as statistics
from astakos.im.models import Resource
from synnefo.util import units
from astakos.im.management.commands import _common as common

RESOURCES = Resource.objects.values_list("name", "desc")

HELP_MSG = """Get available statistics of Astakos Service

Display statistics for users and resources for each Authentication
Provider.

Users
------
 * total: Number of users
 * verified: Number of verified users
 * active: Number of activated users


Resources
---------
For each resource the following information is displayed:

 * used: Current allocated resources
 * limit: Maximum allowed allocation

The available resources are the following:

 * {resources}
""".format(resources="\n * ".join(["%s: %s" % (name, desc)
                                   for name, desc in RESOURCES]))


class Command(SynnefoCommand):
    help = HELP_MSG
    can_import_settings = True

    option_list = SynnefoCommand.option_list + (
        make_option('--unit-style',
                    default='auto',
                    help=("Specify display unit for resource values "
                          "(one of %s); defaults to auto") %
                    common.style_options),
    )

    def handle(self, *args, **options):
        stats = statistics.get_astakos_stats()
        unit_style = options["unit_style"]
        common.check_style(unit_style)

        output_format = options["output_format"]
        if output_format == "json":
            self.stdout.write(json.dumps(stats, indent=4) + "\n")
        elif output_format == "pretty":
            pretty_print_stats(stats, unit_style, self.stdout)
        else:
            raise CommandError("Output format '%s' not supported." %
                               output_format)


def columns_from_fields(fields, values):
    return zip(map(string.lower, fields), [values.get(f, 0) for f in fields])


def pretty_print_stats(stats, unit_style, stdout):
    newline = lambda: stdout.write("\n")

    _datetime = stats.get("datetime")
    stdout.write("datetime: %s\n" % _datetime)
    newline()

    user_stats = stats.get("users", {})
    table = []
    headers = ["Provider Name", "Verified Users", "Active Users",
               "Total Users"]
    for provider, user_info in sorted(user_stats.items()):
        table.append((provider, user_info["verified"], user_info["active"],
                      user_info["total"]))
    pprint_table(stdout, table, headers,
                 title="Users")

    newline()
    resource_stats = stats.get("resources", {})
    total_resources = {}
    headers = ["Resource Name", "Used", "Limit", "Usage"]
    for provider, resources in sorted(resource_stats.items()):
        table = []
        for resource_name, resource_info in sorted(resources.items()):
            unit = resource_info["unit"]
            used = resource_info["used"]
            limit = resource_info["limit"]
            usage = round(used / limit, 1)
            table.append((resource_name,
                          units.show(used, unit, style=unit_style),
                          units.show(limit, unit, style=unit_style),
                          usage))
            # Also count them for total
            total_resources.setdefault(resource_name, {})
            total_resources[resource_name].setdefault("used", 0)
            total_resources[resource_name].setdefault("limit", 0)
            total_resources[resource_name]["used"] += used
            total_resources[resource_name]["limit"] += limit
            total_resources[resource_name]["unit"] = unit
        pprint_table(stdout, table, headers,
                     title="Resources for Provider '%s'" % provider)
        newline()

    if len(resource_stats) > 1:
        table = []
        for resource_name, resource_info in sorted(total_resources.items()):
            unit = resource_info["unit"]
            used = resource_info["used"]
            limit = resource_info["limit"]
            usage = round(used / limit, 1)
            table.append((resource_name,
                          units.show(used, unit, style=unit_style),
                          units.show(limit, unit, style=unit_style),
                          usage))
        pprint_table(stdout, table, headers,
                     title="Resources for all Providers")
        newline()
