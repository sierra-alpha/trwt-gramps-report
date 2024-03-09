#
# Copyright (C) 2024 Shaun Alexander <shaun@sierraalpha.co.nz>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
register(REPORT,
    id   = 'CompactDetailedDescendantReport',
    name = _('Compact Detailed Descendant Report'),
    description = _("Produces one or more compact detailed descendant reports based on a supplied query."),
    version = '0.1',
    gramps_target_version = "5.2",
    status = STABLE,
    fname = 'CompactDetailedDescendantReport.py',
    authors = ["Shaun Alexander"],
    authors_email = ["shaun@sierraalpha.co.nz"],
    category = CATEGORY_TEXT,
    reportclass = 'CompactDetailedDescendantReport',
    optionclass = 'CompactDetailedDescendantOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_CLI],
    require_active = True
    )
