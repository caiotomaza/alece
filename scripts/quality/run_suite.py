# SPDX-License-Identifier: GPL-3.0-only
"""Run tests with durable JUnit/log evidence and never suppress the pytest exit code."""
import os
import subprocess
import sys
from pathlib import Path
from scripts.quality.report_tests import generate
from scripts.quality.test_environment import validate_test_environment


def main():
    validate_test_environment()
    root=Path(__file__).resolve().parents[2]
    out=Path(os.environ.get('ALECE_TEST_RESULTS',str(root/'test-results')))
    out.mkdir(parents=True, exist_ok=True)
    junit=out/'pytest.xml'
    cmd=[sys.executable, '-m', 'pytest', '-q', '-p','no:cacheprovider', '--ignore=tests/browser', '--junitxml='+str(junit), 'tests/']
    print('Iniciando testes isolados; resultados:',out,flush=True)
    with (out/'pytest.log').open('w',encoding='utf-8') as fh:
        with subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            for line in process.stdout:
                sys.stdout.write(line)
                fh.write(line)
            return_code=process.wait()
    generate(root,out/'quality',[junit])
    print('Resultado pytest:', return_code, '; relatório:', out/'quality'/'index.html',flush=True)
    return return_code

if __name__=='__main__':
    sys.exit(main())
