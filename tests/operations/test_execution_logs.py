# SPDX-License-Identifier: GPL-3.0-only
"""No Django/DB required: test container launcher behavior independently."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

PROJECT = Path(__file__).resolve().parents[2]
LAUNCHER = PROJECT / 'docker' / 'logged_start.py'


class ExecutionLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        folder = root / 'docker'
        folder.mkdir()
        self.launcher = folder / 'logged_start.py'
        shutil.copy2(LAUNCHER, self.launcher)
        self.logs = root / 'src' / 'logs'
        self.command = [sys.executable, str(self.launcher), sys.executable, '-c',
                        'import sys; print("INICIO", flush=True); '
                        'sys.stderr.write("FALHA_DE_TESTE\\n"); '
                        'sys.exit(7)']

    def run_launcher(self, enabled):
        env = os.environ.copy()
        env['ALECE_LOG_VALIDACAO'] = enabled
        return subprocess.run(self.command, env=env, text=True,
                              capture_output=True, timeout=15)

    def test_enabled_captures_all_output_and_propagates_exit_status(self):
        result = self.run_launcher('true')
        self.assertEqual(result.returncode, 7)
        self.assertIn('INICIO', result.stdout)
        self.assertIn('FALHA_DE_TESTE', result.stdout)
        files = sorted(self.logs.glob('*.log'))
        self.assertEqual(len(files), 1)
        import re
        self.assertRegex(files[0].name, r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.log$')
        text = files[0].read_text(encoding='utf-8')
        self.assertIn('INICIO', text)
        self.assertIn('FALHA_DE_TESTE', text)
        self.assertIn('codigo_saida=7', text)

    def test_disabled_keeps_console_but_creates_no_file(self):
        result = self.run_launcher('false')
        self.assertEqual(result.returncode, 7)
        self.assertIn('INICIO', result.stdout)
        self.assertIn('FALHA_DE_TESTE', result.stderr)
        self.assertFalse(self.logs.exists())

    def test_rapid_restart_never_overwrites_previous_run(self):
        self.assertEqual(self.run_launcher('true').returncode, 7)
        self.assertEqual(self.run_launcher('true').returncode, 7)
        self.assertEqual(len(list(self.logs.glob('*.log'))), 2)

    def test_visao_geral_has_unconditional_response_at_function_end(self):
        source = (PROJECT / 'src/controller/apps/finance/views.py').read_text(encoding='utf-8')
        functions = [n for n in ast.parse(source).body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name == 'workspace_page']
        self.assertEqual(len(functions), 1)
        self.assertIsInstance(functions[0].body[-1], ast.Return)
        self.assertIsInstance(functions[0].body[-1].value, ast.Call)
        self.assertEqual(functions[0].body[-1].value.func.id, 'render')


if __name__ == '__main__':
    unittest.main()
