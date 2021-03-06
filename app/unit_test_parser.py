# -*- coding: utf-8 -*-
# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cProfile
import io
import pstats
import sys
from timeit import timeit
import unittest

import app.parser
import app.prefs


class ParserTestCases(unittest.TestCase):

    def setUp(self):
        self.parser = app.parser.Parser(app.prefs.Prefs())

    def tearDown(self):
        self.parser = None

    def test_parse(self):
        tests = [
            u"""/* first comment */
two
// second comment
#include "test.h"
void blah();
// No end of line""",
            u"""/* first comment */
two
// second comment
#include "test.h"
void blah();
""",
            u"""/* test includes */
// The malformed include on the next line is a regression test.
#include <test.h"
#include "test.h"
#include <test.h
#include "test.h"

#include <te"st.h>
#include "test>.h"

#include "test.h>
#include <test.h>
#include "test.h
#include <test.h>
void blah();

""",
        ]
        for test in tests:
            #self.assertEqual(test.splitlines(), test.split(u"\n"))
            lines = test.split(u"\n")
            self.prefs = app.prefs.Prefs()
            self.parser.parse(None, test,
                              self.prefs.grammars[u'cpp'], 0, 99999)
            #self.parser.debugLog(print, test)
            self.assertEqual(len(lines), self.parser.rowCount())
            for i, line in enumerate(lines):
                self.assertEqual(self.parser.rowText(i), line)
                self.assertEqual(
                    self.parser.rowTextAndWidth(i), (line, len(line)))
            for node in self.parser.parserNodes:
                # These tests have no double wide characters.
                self.assertEqual(node[app.parser.kBegin],
                                 node[app.parser.kVisual])
            self.parser.debug_checkLines(None, test)

    def test_parse_cpp_literal(self):
        test = u"""/* first comment */
char stuff = R"mine(two
// not a comment)mine";
void blah();
"""
        self.prefs = app.prefs.Prefs()
        self.parser.parse(None, test, self.prefs.grammars['cpp'], 0,
                          99999)
        # self.parser.debugLog(print, test)
        self.assertEqual(self.parser.rowText(0), u"/* first comment */")
        self.assertEqual(self.parser.rowText(1), u"""char stuff = R"mine(two""")
        self.assertEqual(
            self.parser.grammarAt(0, 0),
            self.prefs.grammars[u'cpp_block_comment'])
        self.assertEqual(
            self.parser.grammarAt(1, 8), self.prefs.grammars[u'cpp'])
        self.assertEqual(
            self.parser.grammarAt(1, 18),
            self.prefs.grammars[u'cpp_string_literal'])
        self.assertEqual(
            self.parser.grammarAt(3, 7), self.prefs.grammars[u'cpp'])

    def test_parse_rs_raw_string(self):
        test = u"""// one
let stuff = r###"two
not an "## end
ignored " quote"###;
fn main { }
// two
"""
        self.prefs = app.prefs.Prefs()
        self.parser.parse(None, test, self.prefs.grammars[u'rs'], 0,
                          99999)
        self.assertEqual(self.parser.rowText(0), u"// one")
        self.assertEqual(self.parser.rowText(1), u"""let stuff = r###"two""")
        self.assertEqual(
            self.parser.grammarAt(0, 0),
            self.prefs.grammars[u'cpp_line_comment'])
        self.assertEqual(
            self.parser.grammarAt(1, 8), self.prefs.grammars[u'rs'])
        self.assertEqual(
            self.parser.grammarAt(1, 18), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(2, 12), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(3, 15), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(3, 12), self.prefs.grammars[u'rs_raw_string'])
        self.assertEqual(
            self.parser.grammarAt(4, 7), self.prefs.grammars[u'rs'])

    def test_parse_tabs(self):
        test = u"""\t<tab
\t <tab+space
 \t<space+tab
\ta<
a\t<
some text.>\t<
\t\t<2tabs
line\twith\ttabs
ends with tab>\t
\t
parse\t\t\tz
"""
        self.prefs = app.prefs.Prefs()
        p = self.parser
        self.parser.parse(None, test, self.prefs.grammars[u'rs'], 0,
                          99999)
        if 0:
            print("")
            for i,t in enumerate(test.splitlines()):
                print("{}: {}".format(i, repr(t)))
            p.debugLog(print, test)

        self.assertEqual(p.rowCount(), 12)

        self.assertEqual(p.rowText(0), u"\t<tab")
        self.assertEqual(p.rowText(1), u"\t <tab+space")
        self.assertEqual(p.rowText(2), u" \t<space+tab")
        self.assertEqual(p.rowText(3), u"\ta<")
        self.assertEqual(p.rowText(4), u"a\t<")
        self.assertEqual(p.rowText(5), u"some text.>\t<")
        self.assertEqual(p.rowText(6), u"\t\t<2tabs")
        self.assertEqual(p.rowText(7), u"line\twith\ttabs")
        self.assertEqual(p.rowText(8), u"ends with tab>\t")
        self.assertEqual(p.rowText(9), u"\t")
        self.assertEqual(p.rowText(10), u"parse\t\t\tz")
        self.assertEqual(p.rowText(11), u"")

        self.assertEqual(p.rowTextAndWidth(0), (u"\t<tab", 12))
        self.assertEqual(p.rowTextAndWidth(1), (u"\t <tab+space", 19))
        self.assertEqual(p.rowTextAndWidth(2), (u" \t<space+tab", 18))
        self.assertEqual(p.rowTextAndWidth(3), (u"\ta<", 10))
        self.assertEqual(p.rowTextAndWidth(4), (u"a\t<", 9))
        self.assertEqual(p.rowTextAndWidth(5), (u"some text.>\t<", 17))
        self.assertEqual(p.rowTextAndWidth(6), (u"\t\t<2tabs", 22))
        self.assertEqual(p.rowTextAndWidth(7), (u"line\twith\ttabs", 20))
        self.assertEqual(p.rowTextAndWidth(8), (u"ends with tab>\t", 16))
        self.assertEqual(p.rowTextAndWidth(9), (u"\t", 8))

        self.assertEqual(p.rowWidth(0), 12)
        self.assertEqual(p.rowWidth(1), 19)
        self.assertEqual(p.rowWidth(2), 18)
        self.assertEqual(p.rowWidth(3), 10)
        self.assertEqual(p.rowWidth(4), 9)
        self.assertEqual(p.rowWidth(5), 17)
        self.assertEqual(p.rowWidth(6), 22)
        self.assertEqual(p.rowWidth(7), 20)
        self.assertEqual(p.rowWidth(8), 16)
        self.assertEqual(p.rowWidth(9), 8)

        self.assertEqual(p.grammarIndexFromRowCol(0, 0), 1)
        self.assertEqual(p.grammarIndexFromRowCol(0, 7), 1)
        self.assertEqual(p.grammarIndexFromRowCol(0, 8), 2)
        self.assertEqual(p.grammarIndexFromRowCol(1, 0), 1)

        #self.assertEqual(p.grammarAt(0, 0), 0)


        self.assertEqual(p.nextCharRowCol(999999, 0), None)
        # Test u"\t<tab".
        self.assertEqual(p.nextCharRowCol(0, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(0, 1), (0, 7))
        self.assertEqual(p.nextCharRowCol(0, 7), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 8), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 11), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 12), (1, -12))
        # Test u"\t\t<2tabs".
        self.assertEqual(p.nextCharRowCol(6, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 8), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 16), (0, 1))
        self.assertEqual(p.nextCharRowCol(6, 22), (1, -22))
        # Test u"\t".
        self.assertEqual(p.nextCharRowCol(9, 0), (0, 8))
        self.assertEqual(p.nextCharRowCol(9, 8), (1, -8))
        # Test u"parse\t\t\tz".
        self.assertEqual(p.nextCharRowCol(10, 0), (0, 1))
        self.assertEqual(p.nextCharRowCol(10, 4), (0, 1))
        self.assertEqual(p.nextCharRowCol(10, 5), (0, 3))
        self.assertEqual(p.nextCharRowCol(10, 8), (0, 8))
        self.assertEqual(p.nextCharRowCol(10, 16), (0, 8))
        self.assertEqual(p.nextCharRowCol(10, 24), (0, 1))
        self.assertEqual(p.nextCharRowCol(10, 25), (1, -25))
        self.assertEqual(p.nextCharRowCol(11, 0), None)

        # Test u"\t<tab".
        self.assertEqual(p.priorCharRowCol(0, 0), None)
        self.assertEqual(p.priorCharRowCol(0, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(0, 7), (0, -7))
        # Test u"\t\t<2tabs".
        self.assertEqual(p.priorCharRowCol(6, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 5), (0, -5))
        self.assertEqual(p.priorCharRowCol(6, 8), (0, -8))
        self.assertEqual(p.priorCharRowCol(6, 9), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 15), (0, -7))
        self.assertEqual(p.priorCharRowCol(6, 16), (0, -8))
        self.assertEqual(p.priorCharRowCol(6, 17), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 18), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 19), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 20), (0, -1))
        # Test u"\t".
        self.assertEqual(p.priorCharRowCol(9, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(9, 5), (0, -5))
        self.assertEqual(p.priorCharRowCol(9, 8), (0, -8))

        # Test u"\t<tab".
        self.assertEqual(p.dataOffset(0, 0), 0)
        self.assertEqual(p.dataOffset(0, 1), 0)
        self.assertEqual(p.dataOffset(0, 2), 0)
        self.assertEqual(p.dataOffset(0, 3), 0)
        self.assertEqual(p.dataOffset(0, 7), 0)
        self.assertEqual(p.dataOffset(0, 8), 1)
        self.assertEqual(p.dataOffset(0, 9), 2)
        self.assertEqual(p.dataOffset(0, 12), 5)
        self.assertEqual(p.dataOffset(0, 13), 6)
        self.assertEqual(p.dataOffset(0, 99), None)
        # Test u"\t <tab+space".
        self.assertEqual(p.dataOffset(1, 0), 6)
        self.assertEqual(p.dataOffset(1, 1), 6)
        self.assertEqual(p.dataOffset(1, 2), 6)
        self.assertEqual(p.dataOffset(1, 3), 6)
        self.assertEqual(p.dataOffset(1, 7), 6)
        self.assertEqual(p.dataOffset(1, 8), 7)
        self.assertEqual(p.dataOffset(1, 12), 11)
        self.assertEqual(p.dataOffset(1, 14), 13)
        self.assertEqual(p.dataOffset(1, 19), 18)
        self.assertEqual(p.dataOffset(1, 29), None)
        # Test u" \t<space+tab".
        self.assertEqual(p.dataOffset(2, 0), 19)
        self.assertEqual(p.dataOffset(2, 1), 20)
        self.assertEqual(p.dataOffset(2, 2), 20)
        self.assertEqual(p.dataOffset(2, 12), 25)
        # Test u"\ta<".
        # Test u"a\t<".
        self.assertEqual(p.dataOffset(4, 0), 36)
        self.assertEqual(p.dataOffset(4, 1), 37)
        self.assertEqual(p.dataOffset(4, 2), 37)
        # Test u"some text.>\t<".
        # Test u"\t\t<2tabs".
        self.assertEqual(p.dataOffset(6, 0), 54)
        self.assertEqual(p.dataOffset(6, 7), 54)
        self.assertEqual(p.dataOffset(6, 8), 55)
        self.assertEqual(p.dataOffset(6, 15), 55)
        self.assertEqual(p.dataOffset(6, 16), 56)
        self.assertEqual(p.dataOffset(6, 17), 57)
        # Test u"line\twith\ttabs".
        # Test u"ends with tab>\t".
        # Test u"\t".
        # Test u"parse\t\t\tz".
        self.assertEqual(p.dataOffset(10, 0), 96)
        self.assertEqual(p.dataOffset(10, 4), 100)
        self.assertEqual(p.dataOffset(10, 5), 101)
        self.assertEqual(p.dataOffset(10, 6), 101)
        self.assertEqual(p.dataOffset(10, 7), 101)
        self.assertEqual(p.dataOffset(10, 8), 102)
        self.assertEqual(p.dataOffset(10, 9), 102)
        self.assertEqual(p.dataOffset(10, 15), 102)
        self.assertEqual(p.dataOffset(10, 16), 103)
        self.assertEqual(p.dataOffset(10, 23), 103)
        self.assertEqual(p.dataOffset(10, 24), 104)
        self.assertEqual(p.dataOffset(10, 25), 105)

    def test_parse_mixed(self):
        test = u"""ち\t<tab
\tち<
\t<ち
sちome text.>\t<
line\tち\ttabs
\tち
ち\t\t\tz
Здравствуйте
こんにちはtranslate
"""
        self.prefs = app.prefs.Prefs()
        p = self.parser
        self.parser.parse(None, test, self.prefs.grammars[u'rs'], 0,
                          99999)
        if 0:
            print("")
            for i,t in enumerate(test.splitlines()):
                print("{}: {}".format(i, repr(t)))
            p.debugLog(print, test)

        self.assertEqual(p.rowCount(), 10)

        self.assertEqual(p.rowText(0), u"ち\t<tab")
        self.assertEqual(p.rowText(1), u"\tち<")
        self.assertEqual(p.rowText(2), u"\t<ち")
        self.assertEqual(p.rowText(3), u"sちome text.>\t<")
        self.assertEqual(p.rowText(4), u"line\tち\ttabs")
        self.assertEqual(p.rowText(5), u"\tち")
        self.assertEqual(p.rowText(6), u"ち\t\t\tz")
        self.assertEqual(p.rowText(7), u"Здравствуйте")
        self.assertEqual(p.rowText(8), u"こんにちはtranslate")
        self.assertEqual(p.rowText(9), u"")

        self.assertEqual(p.rowTextAndWidth(0), (u"ち\t<tab", 12))
        self.assertEqual(p.rowTextAndWidth(1), (u"\tち<", 11))
        self.assertEqual(p.rowTextAndWidth(2), (u"\t<ち", 11))
        self.assertEqual(p.rowTextAndWidth(3), (u"sちome text.>\t<", 17))
        self.assertEqual(p.rowTextAndWidth(4), (u"line\tち\ttabs", 20))
        self.assertEqual(p.rowTextAndWidth(5), (u"\tち", 10))
        self.assertEqual(p.rowTextAndWidth(6), (u"ち\t\t\tz", 25))
        self.assertEqual(p.rowTextAndWidth(7), (u"Здравствуйте", 12))
        self.assertEqual(p.rowTextAndWidth(8), (u"こんにちはtranslate", 19))
        self.assertEqual(p.rowTextAndWidth(9), (u"", 0))

        self.assertEqual(p.rowWidth(0), 12)
        self.assertEqual(p.rowWidth(1), 11)
        self.assertEqual(p.rowWidth(2), 11)
        self.assertEqual(p.rowWidth(3), 17)
        self.assertEqual(p.rowWidth(4), 20)
        self.assertEqual(p.rowWidth(5), 10)
        self.assertEqual(p.rowWidth(6), 25)
        self.assertEqual(p.rowWidth(7), 12)
        self.assertEqual(p.rowWidth(8), 19)
        self.assertEqual(p.rowWidth(9), 0)

        self.assertEqual(p.grammarIndexFromRowCol(0, 0), 1)
        self.assertEqual(p.grammarIndexFromRowCol(0, 7), 2)
        self.assertEqual(p.grammarIndexFromRowCol(0, 8), 3)
        self.assertEqual(p.grammarIndexFromRowCol(1, 0), 1)

        self.assertEqual(p.nextCharRowCol(999999, 0), None)
        # Test u"ち\t<tab".
        self.assertEqual(p.nextCharRowCol(0, 0), (0, 2))
        self.assertEqual(p.nextCharRowCol(0, 1), (0, 2))
        self.assertEqual(p.nextCharRowCol(0, 2), (0, 6))
        self.assertEqual(p.nextCharRowCol(0, 8), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 11), (0, 1))
        self.assertEqual(p.nextCharRowCol(0, 12), (1, -12))
        # Test u"ち\t\t\tz".
        self.assertEqual(p.nextCharRowCol(6, 0), (0, 2))
        self.assertEqual(p.nextCharRowCol(6, 8), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 16), (0, 8))
        self.assertEqual(p.nextCharRowCol(6, 25), (1, -25))
        # Test u"".
        self.assertEqual(p.nextCharRowCol(9, 0), None)

        # Test u"ち\t<tab".
        self.assertEqual(p.priorCharRowCol(0, 0), None)
        self.assertEqual(p.priorCharRowCol(0, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(0, 2), (0, -2))
        self.assertEqual(p.priorCharRowCol(0, 3), (0, -1))
        self.assertEqual(p.priorCharRowCol(0, 7), (0, -5))
        # Test u"ち\t\t\tz".
        self.assertEqual(p.priorCharRowCol(6, 1), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 5), (0, -3))
        self.assertEqual(p.priorCharRowCol(6, 8), (0, -6))
        self.assertEqual(p.priorCharRowCol(6, 9), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 15), (0, -7))
        self.assertEqual(p.priorCharRowCol(6, 16), (0, -8))
        self.assertEqual(p.priorCharRowCol(6, 17), (0, -1))
        self.assertEqual(p.priorCharRowCol(6, 18), (0, -2))
        self.assertEqual(p.priorCharRowCol(6, 19), (0, -3))
        self.assertEqual(p.priorCharRowCol(6, 20), (0, -4))

        # Test u"ち\t<tab".
        self.assertEqual(p.dataOffset(0, 0), 0)
        self.assertEqual(p.dataOffset(0, 1), 0)
        self.assertEqual(p.dataOffset(0, 2), 1)
        self.assertEqual(p.dataOffset(0, 3), 1)
        self.assertEqual(p.dataOffset(0, 7), 1)
        self.assertEqual(p.dataOffset(0, 8), 2)
        self.assertEqual(p.dataOffset(0, 9), 3)
        self.assertEqual(p.dataOffset(0, 12), 6)
        self.assertEqual(p.dataOffset(0, 13), 7)
        self.assertEqual(p.dataOffset(0, 99), None)
        # Test u"\tち<".
        self.assertEqual(p.dataOffset(1, 0), 7)
        self.assertEqual(p.dataOffset(1, 1), 7)
        self.assertEqual(p.dataOffset(1, 2), 7)
        self.assertEqual(p.dataOffset(1, 3), 7)
        self.assertEqual(p.dataOffset(1, 7), 7)
        self.assertEqual(p.dataOffset(1, 8), 8)
        self.assertEqual(p.dataOffset(1, 12), 10)
        self.assertEqual(p.dataOffset(1, 14), None)
        # Test u"\t<ち".
        self.assertEqual(p.dataOffset(2, 0), 11)
        self.assertEqual(p.dataOffset(2, 1), 11)
        self.assertEqual(p.dataOffset(2, 2), 11)
        self.assertEqual(p.dataOffset(2, 12), 14)
        # Test u"sちome text.>\t<".
        # Test u"line\tち\ttabs".
        self.assertEqual(p.dataOffset(4, 0), 30)
        self.assertEqual(p.dataOffset(4, 1), 31)
        self.assertEqual(p.dataOffset(4, 2), 32)
        # Test u"\tち".
        self.assertEqual(p.dataOffset(5, 0), 42)
        self.assertEqual(p.dataOffset(5, 1), 42)
        self.assertEqual(p.dataOffset(5, 7), 42)
        self.assertEqual(p.dataOffset(5, 8), 43)
        # Test u"ち\t\t\tz".
        self.assertEqual(p.dataOffset(6, 0), 45)
        self.assertEqual(p.dataOffset(6, 7), 46)
        self.assertEqual(p.dataOffset(6, 8), 47)
        self.assertEqual(p.dataOffset(6, 15), 47)
        self.assertEqual(p.dataOffset(6, 16), 48)
        self.assertEqual(p.dataOffset(6, 17), 48)
        # Test u"Здравствуйте".
        # Test u"こんにちはtranslate".
        # Test u"".

    if 0:

        def test_profile_parse(self):
            profile = cProfile.Profile()
            parser = app.parser.Parser()
            path = u'app/actions.py'
            data = io.open(path).read()
            fileType = self.prefs.getFileType(path)
            grammar = self.prefs.getGrammar(fileType)

            profile.enable()
            parser.parse(data, grammar, 0, sys.maxsize)
            profile.disable()

            output = io.StringIO.StringIO()
            stats = pstats.Stats(
                profile, stream=output).sort_stats(u'cumulative')
            stats.print_stats()
            print(output.getvalue())
