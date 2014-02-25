"""
Unit tests to avoid errors of the past. These are also all tests that didn't
found a good place in any other testing module.
"""

import os
import textwrap

from .helpers import TestCase, cwd_at

import pytest
import jedi
from jedi._compatibility import u
from jedi import Script
from jedi import api
from jedi.evaluate import imports
from jedi.parser import Parser

#jedi.set_debug_function()


class TestRegression(TestCase):
    def test_goto_definition_cursor(self):

        s = ("class A():\n"
             "    def _something(self):\n"
             "        return\n"
             "    def different_line(self,\n"
             "                   b):\n"
             "        return\n"
             "A._something\n"
             "A.different_line"
             )

        in_name = 2, 9
        under_score = 2, 8
        cls = 2, 7
        should1 = 7, 10
        diff_line = 4, 10
        should2 = 8, 10

        def get_def(pos):
            return [d.description for d in Script(s, *pos).goto_definitions()]

        in_name = get_def(in_name)
        under_score = get_def(under_score)
        should1 = get_def(should1)
        should2 = get_def(should2)

        diff_line = get_def(diff_line)

        assert should1 == in_name
        assert should1 == under_score

        assert should2 == diff_line

        self.assertRaises(jedi.NotFoundError, get_def, cls)

    @pytest.mark.skip('Skip for now, test case is not really supported.')
    @cwd_at('jedi')
    def test_add_dynamic_mods(self):
        fname = '__main__.py'
        api.settings.additional_dynamic_modules = [fname]
        # Fictional module that defines a function.
        src1 = "def r(a): return a"
        # Other fictional modules in another place in the fs.
        src2 = 'from .. import setup; setup.r(1)'
        imports.load_module(os.path.abspath(fname), src2)
        result = Script(src1, path='../setup.py').goto_definitions()
        assert len(result) == 1
        assert result[0].description == 'class int'

    def test_os_nowait(self):
        """ github issue #45 """
        s = Script("import os; os.P_").completions()
        assert 'P_NOWAIT' in [i.name for i in s]

    def test_points_in_completion(self):
        """At some point, points were inserted into the completions, this
        caused problems, sometimes.
        """
        c = Script("if IndentationErr").completions()
        assert c[0].name == 'IndentationError'
        self.assertEqual(c[0].complete, 'or')

    def test_no_statement_parent(self):
        source = textwrap.dedent("""
        def f():
            pass

        class C:
            pass

        variable = f or C""")
        defs = Script(source, column=3).goto_definitions()
        defs = sorted(defs, key=lambda d: d.line)
        self.assertEqual([d.description for d in defs],
                         ['def f', 'class C'])

    def test_end_pos(self):
        # jedi issue #150
        s = u("x()\nx( )\nx(  )\nx (  )")
        parser = Parser(s)
        for i, s in enumerate(parser.module.statements, 3):
            for c in s.expression_list():
                self.assertEqual(c.execution.end_pos[1], i)

    def check_definition_by_marker(self, source, after_cursor, names):
        r"""
        Find definitions specified by `after_cursor` and check what found

        For example, for the following configuration, you can pass
        ``after_cursor = 'y)'``.::

            function(
                x, y)
                   \
                    `- You want cursor to be here
        """
        source = textwrap.dedent(source)
        for (i, line) in enumerate(source.splitlines()):
            if after_cursor in line:
                break
        column = len(line) - len(after_cursor)
        defs = Script(source, i + 1, column).goto_definitions()
        print(defs)
        assert [d.name for d in defs] == names

    def test_backslash_continuation(self):
        """
        Test that ModuleWithCursor.get_path_until_cursor handles continuation
        """
        self.check_definition_by_marker(r"""
        x = 0
        a = \
          [1, 2, 3, 4, 5, 6, 7, 8, 9, x]  # <-- here
        """, ']  # <-- here', ['int'])

        # completion in whitespace
        s = 'asdfxyxxxxxxxx sds\\\n    hello'
        assert Script(s, 2, 4).goto_assignments() == []

    def test_backslash_continuation_and_bracket(self):
        self.check_definition_by_marker(r"""
        x = 0
        a = \
          [1, 2, 3, 4, 5, 6, 7, 8, 9, (x)]  # <-- here
        """, '(x)]  # <-- here', [])

    def test_generator(self):
        # Did have some problems with the usage of generator completions this
        # way.
        s = "def abc():\n" \
            "    yield 1\n" \
            "abc()."
        assert Script(s).completions()
