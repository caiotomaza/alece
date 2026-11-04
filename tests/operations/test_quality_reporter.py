# SPDX-License-Identifier: GPL-3.0-only
"""The reporter must distinguish execution evidence from declared tests."""
from scripts.quality.report_tests import generate


def test_reporter_marks_missing_junit_as_not_executed(tmp_path):
    testfile=tmp_path/'tests'/'finance'/'test_sample.py'
    testfile.parent.mkdir(parents=True)
    testfile.write_text('def test_hypothetical():\n    assert True\n')
    report=generate(tmp_path,tmp_path/'reports',[])
    assert report['inventory_declared']==1
    assert report['junit_executed_cases']==0
    assert report['inventory_counts']=={'NAO_EXECUTADO':1}


def test_reporter_reflects_failure_from_junit(tmp_path):
    testfile=tmp_path/'tests'/'finance'/'test_sample.py'
    testfile.parent.mkdir(parents=True)
    testfile.write_text('def test_hypothetical():\n    assert True\n')
    xml=tmp_path/'result.xml'
    xml.write_text('''<testsuite><testcase classname="tests.finance.test_sample" name="test_hypothetical"><failure message="test failure"/></testcase></testsuite>''')
    report=generate(tmp_path,tmp_path/'reports',[xml])
    assert report['junit_result_counts']=={'FALHOU':1}
    assert report['inventory_counts']=={'FALHOU':1}
