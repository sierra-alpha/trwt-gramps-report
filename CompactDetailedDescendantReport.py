# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Mostly taken from the built in Detailed Descendant Report, credit to those
# Contributors here:
#
# Copyright (C) 2000-2002 Bruce J. DeGrasse
# Copyright (C) 2000-2007 Donald N. Allingham
# Copyright (C) 2007-2012 Brian G. Matherly
# Copyright (C) 2007      Robert Cawley  <rjc@cawley.id.au>
# Copyright (C) 2008-2009 James Friedmann <jfriedmannj@gmail.com>
# Copyright (C) 2009      Benny Malengier <benny.malengier@gramps-project.org>
# Copyright (C) 2010      Jakim Friant
# Copyright (C) 2010      Vlada Perić <vlada.peric@gmail.com>
# Copyright (C) 2011      Matt Keenan <matt.keenan@gmail.com>
# Copyright (C) 2011      Tim G L Lyons
# Copyright (C) 2012      lcc <lcc@6zap.com>
# Copyright (C) 2013-2014 Paul Franklin
# Copyright (C) 2015      Craig J. Anderson
# Copyright (C) 2017      Robert Carnell <bertcarnell_at_gmail.com>
#
# And for modifying to make this custom Compact Detailed Descendant Report
#
# Copyright (C) 2024      Shaun Alexander <shaun@sierraalpha.co.nz>
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

"""Reports/Text Reports/Compact Detailed Descendant Report"""

# ------------------------------------------------------------------------
#
# standard python modules
#
# ------------------------------------------------------------------------
from functools import partial


# ------------------------------------------------------------------------
#
# pypi packages included with this addon
#
# ------------------------------------------------------------------------
from dateutil.parser import parse, ParserError

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.lib import FamilyRelType
from gramps.gen.datehandler import get_date

from gramps.gen.utils.db import (
    get_birth_or_fallback,
    get_death_or_fallback,
)
from gramps.gen.plug.menu import (
    BooleanOption,
    NumberOption,
    PersonOption,
    EnumeratedListOption,
)
from gramps.gen.plug.docgen import (
    FONT_SANS_SERIF,
    FONT_SERIF,
    FontStyle,
    INDEX_TYPE_ALP,
    INDEX_TYPE_TOC,
    IndexMark,
    PARA_ALIGN_CENTER,
    PARA_ALIGN_RIGHT,
    ParagraphStyle,
    TableCellStyle,
    TableStyle,
)
from gramps.gen.plug.report import Report, Bibliography
from gramps.gen.plug.report import endnotes
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.display.place import displayer as _pd
from gramps.gen.display.name import displayer as _nd
from gramps.gen.proxy import CacheProxyDb


# ------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------
HENRY = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ------------------------------------------------------------------------
#
# Printinfo
#
# ------------------------------------------------------------------------
class Printinfo:
    """
    A base class used to help make the individual numbering system classes.
    This class must first be initialized with set_class_vars
    """

    def __init__(
        self,
        doc,
        database,
        dnumber,
        deathage,
        name_display,
        rlocale,
        pformat,
    ):
        # classes
        self._name_display = name_display
        self.doc = doc
        self.database = database
        self.dnumber = dnumber
        # variables
        self.deathage = deathage
        self.rlocale = rlocale  # Temp for now to see if I need to fix it
        self._ = rlocale.translation.sgettext  # needed for English
        self._get_date = rlocale.get_date
        self.pformat = pformat

    def get_person_mark(self, person):
        """
        Return a IndexMark that can be used to index a person in a report

        :param person: the key is for
        """
        if not person:
            return None

        def get_name(person):
            """
            Return a name string built from the components of the Name instance,
            in the form of: surname, Firstname.
            """
            first = person.get_primary_name().get_first_name()
            surname = person.get_primary_name().get_surname().upper()
            if person.get_primary_name().get_suffix():
                # Translators: needed for Arabic, ignore otherwise
                return _("%(surname)s, %(first)s %(suffix)s") % {
                    "surname": surname,
                    "first": first,
                    "suffix": person.get_primary_name().get_suffix(),
                }
            else:
                # Translators: needed for Arabic, ignore otherwise
                return _("%(str1)s, %(str2)s") % {"str1": surname, "str2": first}

        name = get_name(person)
        index_text = self.dnumber.get(person.handle, "")
        key = "{} {}...".format(name, "#:{}".format(index_text) if index_text else "")

        return IndexMark(key, INDEX_TYPE_ALP)

    def __date_place(self, event):
        """return the date and/or place an event happened"""
        if event:
            date = self._get_date(event.get_date_object())
            place_handle = event.get_place_handle()
            if place_handle:
                place = _pd.display_event(self.database, event, self.pformat)
                return "%(event_abbrev)s %(date)s - %(place)s" % {
                    "event_abbrev": event.type.get_abbreviation(self._),
                    "date": date,
                    "place": place,
                }
            else:
                return "%(event_abbrev)s %(date)s" % {
                    "event_abbrev": event.type.get_abbreviation(self._),
                    "date": date,
                }
        return ""

    def __get_age_at_death(self, person):
        """
        Calculate the age the person died.

        Returns None or the age.
        """
        birth_ref = person.get_birth_ref()
        if birth_ref:
            birth_event = self.database.get_event_from_handle(birth_ref.ref)
            birth = birth_event.get_date_object()
            birth_year_valid = birth.get_year_valid()
        else:
            birth_year_valid = False
        death_ref = person.get_death_ref()
        if death_ref:
            death_event = self.database.get_event_from_handle(death_ref.ref)
            death = death_event.get_date_object()
            death_year_valid = death.get_year_valid()
        else:
            death_year_valid = False

        # without at least a year for each event no age can be calculated
        if birth_year_valid and death_year_valid:
            span = death - birth
            if span and span.is_valid():
                if span:
                    age = span.get_repr(dlocale=self.rlocale)
                else:
                    age = None
            else:
                age = None
        else:
            age = None

        return age

    def print_details(self, person, style):
        """print descriptive details for a person"""

        def process_dates(date):
            try:
                gdate, gdate_text = parse(date, fuzzy_with_tokens=True)
                gdate = gdate.strftime(" %Y")
            except ParserError:
                return ""

            gdatestring = "{}{} {}".format(
                gdate_text[0], gdate, "" if len(gdate_text) <= 1 else gdate_text[-1]
            )
            return gdatestring

        bdate = self.__date_place(get_birth_or_fallback(self.database, person))
        if bdate and process_dates(bdate):
            self.doc.start_paragraph(style)
            self.doc.write_text(process_dates(bdate))
            self.doc.end_paragraph()

        ddate = self.__date_place(get_death_or_fallback(self.database, person))
        if ddate and process_dates(ddate):
            age = self.__get_age_at_death(person)
            self.doc.start_paragraph(style)
            self.doc.write_text(
                "{}{}".format(process_dates(ddate), " ({})".format(age) if age else "")
            )
            self.doc.end_paragraph()

    def print_person(
        self,
        person,
        main_entry=True,
        spouse_relationship=None,
        person_style=None,
        person_deets_style=None,
    ):
        """print the person"""

        spouse_relationship_text = (
            {
                FamilyRelType.MARRIED: "M.",
                FamilyRelType.CIVIL_UNION: "CU.",
            }.get(spouse_relationship.value, "")
            if spouse_relationship
            else ""
        )

        display_num = self.dnumber.get(person.handle)
        display_num = "{} ".format(display_num) if display_num else ""
        person_style = person_style or (
            "CDDR-First-Entry" if main_entry else "CDDR-ChildListSimple"
        )
        self.doc.start_paragraph(person_style, display_num if main_entry else "")
        mark = self.get_person_mark(person)
        self.doc.start_bold() if main_entry else None
        display_name = self._name_display.display(person)
        self.doc.write_text(
            "={} {}{}".format(
                " ({})".format(spouse_relationship_text)
                if spouse_relationship_text
                else "",
                display_name,
                ". See reference {} for their individual record".format(display_num)
                if display_num
                else "",
            )
            if spouse_relationship
            else display_name,
            mark,
        )
        self.doc.end_bold() if main_entry else None
        self.doc.end_paragraph()
        self.print_details(
            person,
            person_deets_style
            or ("CDDR-First-Details" if main_entry else "CDDR-ChildListSimple"),
        )

    def print_spouse(
        self, spouse_handle, relationship, person_style=None, person_deets_style=None
    ):
        """print the spouse"""
        # Currently print_spouses is the same for all numbering systems.
        if spouse_handle:
            spouse = self.database.get_person_from_handle(spouse_handle)
            self.print_person(
                spouse,
                main_entry=False,
                spouse_relationship=relationship,
                person_style=person_style or "CDDR-First-Entry-Spouse",
                person_deets_style=person_deets_style or "CDDR-First-Details-Spouse",
            )
        # else:
        #     self.doc.start_paragraph(person_style or "CDDR-First-Entry-Spouse")
        #     self.doc.write_text(self._("= %(spouse)s") % {"spouse": self._("Unknown")})
        #     self.doc.end_paragraph()

    def print_reference(self, person, display_num, style, is_spouse=False):
        """print the reference"""
        # Person and their family have already been printed so
        # print reference here
        if person:
            mark = self.get_person_mark(person)
            self.doc.start_paragraph(style)
            name = self._name_display.display(person)
            self.doc.write_text(
                "{}{}, see {}".format(
                    "= " if is_spouse else "",
                    name,
                    "{} {}.".format(
                        display_num,
                        ("for details" if not is_spouse else "for family details"),
                    ),
                ),
                mark,
            )
            self.doc.end_paragraph()


# ------------------------------------------------------------------------
#
#
#
# ------------------------------------------------------------------------
class CompactDetailedDescendantReport(Report):
    """Compact Detailed Descendant Report"""

    def __init__(self, database, options, user):
        """
        Create the CompactDetailedDescendantReport object that produces the report.

        The arguments are:

        database        - the Gramps database instance
        options         - instance of the Options class for this report

        This report needs the following parameters (class variables)
        that come in the options class.

        gen           - Maximum number of generations to include.
        pagebgg       - Whether to include page breaks between generations.
        listc         - Whether to list children.
        numbering     - The descendancy numbering system to be utilized.
        pid           - The Gramps ID of the center person for the report.
        name_format   - Preferred format to display names
        incl_private  - Whether to include private data
        living_people - How to handle living people
        years_past_death - Consider as living this many years after death
        """
        Report.__init__(self, database, options, user)

        self.map = {}
        self.printed_people_refs = {}

        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.set_locale(get_value("trans"))

        stdoptions.run_date_format_option(self, menu)

        stdoptions.run_private_data_option(self, menu)
        stdoptions.run_living_people_option(self, menu, self._locale)
        self.database = CacheProxyDb(self.database)
        self._db = self.database

        self.max_generations = get_value("gen")
        self.pgbrk = get_value("pagebbg")
        self.listchildren = get_value("listc")
        self.numbering = get_value("numbering")

        pid = get_value("pid")
        self.center_person = self._db.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid)

        self.gen_handles = {}
        self.gen_keys = []
        self.dnumber = {}

        if self.numbering == "Henry":
            self.apply_henry_filter(self.center_person.get_handle(), 1, "1")
        elif self.numbering == "Modified Henry":
            self.apply_mhenry_filter(self.center_person.get_handle(), 1, "1")
        elif self.numbering == "d'Aboville":
            self.apply_daboville_filter(self.center_person.get_handle(), 1, "1")
        else:
            raise AttributeError("no such numbering: '%s'" % self.numbering)

        stdoptions.run_name_format_option(self, menu)

        lifespan = menu.get_option_by_name("lifespan").get_value()

        stdoptions.run_name_format_option(self, menu)

        pformat = menu.get_option_by_name("place_format").get_value()

        self.print_people = Printinfo(
            self.doc,
            self.database,
            self.dnumber,
            lifespan,
            self._name_display,
            self._locale,
            pformat,
        )
        self.bibli = Bibliography(Bibliography.MODE_DATE | Bibliography.MODE_PAGE)

    def apply_henry_filter(self, person_handle, index, pid, cur_gen=1):
        """Filter for Henry numbering"""
        if (not person_handle) or (cur_gen > self.max_generations):
            return
        if person_handle in self.dnumber:
            if self.dnumber[person_handle] > pid:
                self.dnumber[person_handle] = pid
        else:
            self.dnumber[person_handle] = pid
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)
        index = 0
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_henry_filter(
                    child_ref.ref, _ix + 1, pid + HENRY[index], cur_gen + 1
                )
                index += 1

    def apply_mhenry_filter(self, person_handle, index, pid, cur_gen=1):
        """Filter for Modified Henry numbering"""

        def mhenry():
            """convenience finction"""
            return str(index) if index < 10 else "(" + str(index) + ")"

        if (not person_handle) or (cur_gen > self.max_generations):
            return
        self.dnumber[person_handle] = pid
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)
        index = 1
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_henry_filter(
                    child_ref.ref, _ix + 1, pid + mhenry(), cur_gen + 1
                )
                index += 1

    def apply_daboville_filter(self, person_handle, index, child_num, cur_gen=1):
        """Filter for d'Aboville numbering"""
        if (not person_handle) or (cur_gen > self.max_generations):
            return

        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)

        families_as_child = [
            self._db.get_family_from_handle(x)
            for x in person.get_parent_family_handle_list()
        ]
        is_not_child_of_multiple_fams = len(families_as_child) <= 1
        number = "" if is_not_child_of_multiple_fams else "{"
        for fam_idx, family_as_child in enumerate(families_as_child):
            mother_num = self.dnumber.get(family_as_child.get_mother_handle())
            father_num = self.dnumber.get(family_as_child.get_father_handle())
            number += (
                ""
                if is_not_child_of_multiple_fams
                else "{}{}:[".format(
                    ", " if fam_idx > 0 else "", chr(ord("a") + (fam_idx % 26))
                )
            )
            if mother_num and father_num:
                # We're related twice to the top person
                # find the common number
                split_idx = None
                for idx, (x, y) in enumerate(zip(mother_num, father_num)):
                    if x == y:
                        number += x
                    else:
                        split_idx = idx
                        break
                number += "({}).{}".format(
                    "|".join(
                        sorted(
                            [mother_num[split_idx:], father_num[split_idx:]],
                            key=lambda x: int(x.split(".")[-1]),
                        )
                    ),
                    child_num,
                )
            elif mother_num:
                number += "{}.{}".format(mother_num, child_num)
            elif father_num:
                number += "{}.{}".format(father_num, child_num)
            elif cur_gen == 1:
                # raise ReportError("{}{}{}".format(number, mother_num, father_num))
                number += child_num

            number += "" if is_not_child_of_multiple_fams else "]"

        number += "" if is_not_child_of_multiple_fams else "}"
        self.dnumber[person_handle] = number

        index = 1
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_daboville_filter(child_ref.ref, _ix + 1, index, cur_gen + 1)
                index += 1

    def write_report(self):
        """
        This function is called by the report system and writes the report.
        """

        name = self._name_display.display_name(self.center_person.get_primary_name())
        if not name:
            name = self._("Unknown")

        self.doc.start_paragraph("CDDR-Title")

        # feature request 2356: avoid genitive form
        title = self._("Descendant Report for %(person_name)s") % {"person_name": name}
        mark = IndexMark(title, INDEX_TYPE_TOC, 1)
        self.doc.write_text(title, mark)
        self.doc.end_paragraph()

        for generation, gen_keys in enumerate(self.gen_keys):

            if self.pgbrk and generation > 0:
                self.doc.page_break()
            self.doc.start_paragraph("CDDR-Generation")
            text = self._("Generation %d") % (generation + 1)
            mark = IndexMark(text, INDEX_TYPE_TOC, 2)
            self.doc.write_text(text, mark)
            self.doc.end_paragraph()

            # Need to catch an empty generation
            if generation > 0 and not any(
                z
                for x in gen_keys
                for y in self._db.get_person_from_handle(
                    self.map[x]
                ).get_family_handle_list()
                for z in self._db.get_family_from_handle(y).get_child_ref_list()
            ):

                self.doc.start_paragraph("CDDR-ChildListSimple")
                text = self._(
                    "\nAll people in this generation have no children themselves, so they are displayed "
                    "as children in the previous generation."
                )
                self.doc.write_text(text)
                self.doc.end_paragraph()
                # If everyone in this generation doesn't have any children
                # then we've printed everyone elsewhere so we can skip
                #
                continue

            for key in gen_keys:
                person_handle = self.map[key]
                self.gen_handles[person_handle] = key
                self.write_person(key)

    def write_person(self, key):
        """Output birth, death, parentage, marriage information"""

        person_handle = self.map[key]
        person = self._db.get_person_from_handle(person_handle)
        person_dnum = self.dnumber[person_handle]

        if person_dnum != "1" and not any(
            y
            for x in person.get_family_handle_list()
            for y in self._db.get_family_from_handle(x).get_child_ref_list()
        ):
            # If we have no descendants and we're not the first person then
            # we'll be already printed elsewhere so we can skip
            #
            return

        self.print_people.print_person(person)

        if person_handle not in self.printed_people_refs:
            self.printed_people_refs[person_handle] = self.dnumber[person_handle]

        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            spouse_handle = utils.find_spouse(person, family)

            if spouse_handle in self.printed_people_refs:
                # Just print a reference
                spouse = self.database.get_person_from_handle(spouse_handle)
                self.print_people.print_reference(
                    spouse,
                    self.printed_people_refs[spouse_handle],
                    "CDDR-First-Entry-Spouse",
                    is_spouse=True,
                )
            else:
                self.print_people.print_spouse(spouse_handle, family.get_relationship())

                if spouse_handle and spouse_handle not in self.dnumber:
                    spouse_num = "= of: {} {}".format(
                        self.dnumber[person_handle], self._name_display.display(person)
                    )
                    self.printed_people_refs[spouse_handle] = spouse_num

                if self.listchildren:
                    self.__write_children(family, person)

    def __write_children(self, family, person):
        """
        List the children for the given family.
        :param family: Family
        :param this_descendant: Person (the person that started this write children)
        :return:
        """
        if not family.get_child_ref_list():
            return

        spouse_handle = utils.find_spouse(person, family)
        spouse_name = (
            self._name_display.display(
                self.database.get_person_from_handle(spouse_handle)
            )
            if spouse_handle
            else ""
        )
        self.doc.start_paragraph("CDDR-ChildTitle")
        self.doc.write_text(
            "Children of {}{}".format(
                self._name_display.display(person), " and {}".format(spouse_name) if spouse_name else ""
            )
        )
        self.doc.end_paragraph()

        self.doc.start_table(
            format("child-table-{}".format(family.gramps_id)), "CDDR-ChildTable"
        )
        for child_ref in family.get_child_ref_list():
            self.doc.start_row()
            child_handle = child_ref.ref
            child = self._db.get_person_from_handle(child_handle)
            child_name = self._name_display.display(child)
            if not child_name:
                child_name = self._("Unknown")
            child_mark = self.print_people.get_person_mark(child)

            prefix = ""
            for family_handle in child.get_family_handle_list():
                family = self._db.get_family_from_handle(family_handle)
                if family.get_child_ref_list():
                    prefix = "+ "
                    break

            self.doc.start_cell("CDDR-ChildTableCell")
            self.doc.start_paragraph("CDDR-ChildListLeftSimple")
            if child_handle in self.dnumber:
                self.doc.write_text(prefix + str(self.dnumber[child_handle]))
            else:
                self.doc.write_text(prefix)
            self.doc.end_paragraph()
            self.doc.end_cell()

            self.doc.start_cell("CDDR-ChildTableCell")
            if prefix:
                self.doc.start_paragraph("CDDR-ChildListSimple")
                self.doc.write_text("%s" % child_name, child_mark)
                self.doc.end_paragraph()
            else:
                self.print_people.print_person(
                    child, main_entry=False, person_deets_style="CDDR-First-Details"
                )
                for family_handle in child.get_family_handle_list():

                    family = self._db.get_family_from_handle(family_handle)
                    spouse_handle = utils.find_spouse(child, family)

                    if spouse_handle in self.printed_people_refs:
                        # Just print a reference
                        spouse = self.database.get_person_from_handle(spouse_handle)
                        self.print_people.print_reference(
                            spouse,
                            self.printed_people_refs[spouse_handle],
                            "CDDR-ChildListSimpleIndented",
                            is_spouse=True,
                        )
                    else:
                        self.print_people.print_spouse(
                            spouse_handle,
                            family.get_relationship(),
                            person_style="CDDR-ChildListSimpleIndented",
                        )

                        if spouse_handle and spouse_handle not in self.dnumber:
                            spouse_num = "= of: {} {}".format(
                                self.dnumber[child.handle],
                                self._name_display.display(person),
                            )
                            self.printed_people_refs[spouse_handle] = spouse_num

            self.doc.end_cell()

            self.doc.end_row()

        self.doc.end_table()

    def endnotes(self, obj):
        """write out any endnotes/footnotes"""
        if not obj:
            return ""

        txt = endnotes.cite_source(self.bibli, self._db, obj, self._locale)
        if txt:
            txt = "<super>" + txt + "</super>"
        return txt


# ------------------------------------------------------------------------
#
# CompactDetailedDescendantOptions
#
# ------------------------------------------------------------------------
class CompactDetailedDescendantOptions(MenuReportOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        MenuReportOptions.__init__(self, name, dbase)

    def get_subject(self):
        """Return a string that describes the subject of the report."""
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        return _nd.display(person)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the compact detailed descendant report.
        """

        # Report Options
        category = _("Report Options")
        add_option = partial(menu.add_option, category)

        self.__pid = PersonOption(_("Center Person"))
        self.__pid.set_help(_("The center person for the report"))
        add_option("pid", self.__pid)

        numbering = EnumeratedListOption(_("Numbering system"), "d'Aboville")
        numbering.set_items(
            [
                ("Henry", _("Henry numbering")),
                ("Modified Henry", _("Modified Henry numbering")),
                ("d'Aboville", _("d'Aboville numbering")),
            ]
        )
        numbering.set_help(_("The numbering system to be used"))
        add_option("numbering", numbering)

        structure = EnumeratedListOption(_("Report structure"), "by generation")
        structure.set_items(
            [
                ("by generation", _("show people by generations")),
            ]
        )
        structure.set_help(_("How people are organized in the report"))
        add_option("structure", structure)

        gen = NumberOption(_("Generations"), 10, 1, 100)
        gen.set_help(_("The number of generations to include in the report"))
        add_option("gen", gen)

        lifespan = BooleanOption(_("Show birth and death info"), True)
        lifespan.set_help(
            _("Whether to show birth and death information in the report.")
        )
        add_option("lifespan", lifespan)

        pagebbg = BooleanOption(_("Page break between generations"), False)
        pagebbg.set_help(_("Whether to start a new page after each generation."))
        add_option("pagebbg", pagebbg)

        category = _("Report Options (2)")
        add_option = partial(menu.add_option, category)

        stdoptions.add_name_format_option(menu, category)

        stdoptions.add_place_format_option(menu, category)

        stdoptions.add_private_data_option(menu, category)

        stdoptions.add_living_people_option(menu, category)

        locale_opt = stdoptions.add_localization_option(menu, category)

        stdoptions.add_date_format_option(menu, category, locale_opt)

        # Content

        add_option = partial(menu.add_option, _("Content"))

        # What to include

        add_option = partial(menu.add_option, _("Include"))

        listc = BooleanOption(_("Include children"), True)
        listc.set_help(_("Whether to list children."))
        add_option("listc", listc)

    def make_default_style(self, default_style):
        """Make the default output style for the Detailed Ancestral Report"""
        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=16, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(1)
        para.set_top_margin(0.25)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_("The style used for the title."))
        default_style.add_paragraph_style("CDDR-Title", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=14, italic=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(2)
        para.set_top_margin(0.25)
        para.set_description(_("The style used for the generation header."))
        default_style.add_paragraph_style("CDDR-Generation", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=10, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_left_margin(1.5)  # in centimeters
        para.set_top_margin(0.10)
        para.set_bottom_margin(0.10)
        para.set_description(_("The style used for the children list title."))
        default_style.add_paragraph_style("CDDR-ChildTitle", para)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(2)
        table.set_column_width(0, 25)
        table.set_column_width(1, 75)
        table.set_description(_("The style used for the children list table."))
        default_style.add_table_style("CDDR-ChildTable", table)

        table = TableCellStyle()
        table.set_description(_("The style used for the children list table cells."))
        default_style.add_cell_style("CDDR-ChildTableCell", table)

        font = FontStyle()
        font.set(size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(rmargin=0.25)
        para.set_alignment(PARA_ALIGN_RIGHT)
        para.set_description(_("The style used for the children list numbers."))
        default_style.add_paragraph_style("CDDR-ChildListLeftSimple", para)

        font = FontStyle()
        font.set(size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_description(_("The style used for the Children list text."))
        default_style.add_paragraph_style("CDDR-ChildListSimple", para)

        font = FontStyle()
        font.set(size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(lmargin=0.2)
        para.set_description(_("The style used for the Children list text - indented."))
        default_style.add_paragraph_style("CDDR-ChildListSimpleIndented", para)

        para = ParagraphStyle()
        para.set(lmargin=1.5)
        para.set_top_margin(0.1)
        para.set_description(_("The basic style used for the text display."))
        default_style.add_paragraph_style("CDDR-Entry", para)

        para = ParagraphStyle()
        para.set(lmargin=0.0)
        para.set_top_margin(0.25)
        para.set_description(_("The style used for first level headings."))
        default_style.add_paragraph_style("CDDR-First-Entry", para)

        font = FontStyle()
        font.set(size=8)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(lmargin=0.5)
        para.set_top_margin(0.0)
        para.set_description(_("The style used for the first level details."))
        default_style.add_paragraph_style("CDDR-First-Details", para)

        para = ParagraphStyle()
        para.set(lmargin=0.75)
        para.set_top_margin(0.15)
        para.set_description(_("The style used for first level spouse headings."))
        default_style.add_paragraph_style("CDDR-First-Entry-Spouse", para)

        font = FontStyle()
        font.set(size=8)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(lmargin=1)
        para.set_top_margin(0.0)
        para.set_description(_("The style used for the first level spouse details."))
        default_style.add_paragraph_style("CDDR-First-Details-Spouse", para)

        font = FontStyle()
        font.set(size=10, face=FONT_SANS_SERIF, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.5)
        para.set_top_margin(0.10)
        para.set_description(_("The style used for second level headings."))
        default_style.add_paragraph_style("CDDR-MoreHeader", para)

        font = FontStyle()
        font.set(face=FONT_SERIF, size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.5)
        para.set_top_margin(0.10)
        para.set_description(_("The style used for details."))
        default_style.add_paragraph_style("CDDR-MoreDetails", para)

        endnotes.add_endnote_styles(default_style)


if __name__ == "main":
    options = CompactDetailedDescendantOptions({})
    report = CompactDetailedDescendantReport(options)
    report.write_report()
