# SPDX-License-Identifier: GPL-3.0-only
"""Auditable test inventory and status matrix from JUnit XML; no invented passes."""
from __future__ import annotations
import argparse
import ast
import csv
import html
import json
from pathlib import Path
from collections import Counter
from xml.etree import ElementTree as ET

AREAS = {
    'auth': ('Autenticação', 'Acesso não autorizado, sessão ou recuperação'),
    'configuration': ('Configurações', 'Elevação de privilégios, gestão incorreta'),
    'finance': ('Finanças', 'Saldos incorretos, lançamentos duplicados'),
    'imports': ('Importações', 'Importação parcial ou indevida'),
    'reports': ('Relatórios', 'Vazamento ou perda de integridade'),
    'operations': ('Operações', 'Falha de observabilidade/segurança'),
    'ui': ('Interface', 'Regressão de navegação e visualização'),
    'browser': ('Navegador', 'Jornada real não funcional'),
    'logs': ('Logs', 'Exposição indevida de auditoria'),
    'integrations': ('Integrações de IA', 'Credenciais e autorização'),
}

def _test_functions(root):
    for path in sorted((root / 'tests').rglob('test_*.py')):
        module = '.'.join(path.relative_to(root).with_suffix('').parts)
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        except (SyntaxError, UnicodeError):
            yield {'path':str(path.relative_to(root)),'nodeid':'erro-de-sintaxe', 'module': 'unknown','risk':'Código de teste inválido', 'case':'erro-de-sintaxe'}
            continue
        for obj in tree.body:
            if isinstance(obj,(ast.FunctionDef,ast.AsyncFunctionDef)) and obj.name.startswith('test_'):
                yield _entry(path,root,module,obj.name)
            if isinstance(obj,ast.ClassDef):
                for m in obj.body:
                    if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)) and m.name.startswith('test_'):
                        yield _entry(path,root,module,obj.name+'::'+m.name)

def _entry(path,root,module,case):
    area=path.relative_to(root).parts[1]
    label,risk=AREAS.get(area,(area,'Regressão não classificada'))
    return {'path':str(path.relative_to(root)),'nodeid':str(path.relative_to(root))+'::'+case, 'module':label,'risk':risk,'case':case}

def _junit_results(paths):
    statuses=[]
    for path in paths:
        if not path.is_file(): continue
        try: doc=ET.parse(path)
        except (OSError, ET.ParseError): continue
        for e in doc.findall('.//testcase'):
            children=set(ch.tag for ch in e)
            status = 'FALHOU' if 'failure' in children or 'error' in children else ('IGNORADO' if 'skipped' in children else 'APROVADO')
            statuses.append({'classname':e.get('classname',''), 'name':e.get('name',''), 'status':status,'junit':str(path)})
    return statuses

def generate(root,out,xml):
    out.mkdir(parents=True,exist_ok=True)
    inventory=list(_test_functions(root))
    executed=_junit_results(xml)
    lookup={}
    for e in executed:
        # pytest JUnit classname: tests.auth.test_auth.AuthenticationViewsTests;
        # class::test method is represented as class in classname + method in name.
        lookup.setdefault((e['classname'].replace('.','/'),e['name'].split('[')[0]),[]).append(e)
    for row in inventory:
        path=row['path'].replace('.py','')
        case=row['case'].split('::')
        classname=path if len(case)==1 else path+'/'+case[0]
        match=lookup.get((classname,case[-1]))
        if match:
            values={entry['status'] for entry in match}
            row['status']='FALHOU' if 'FALHOU' in values else ('IGNORADO' if values=={'IGNORADO'} else 'APROVADO')
            row['evidence']='; '.join(sorted({entry['junit'] for entry in match}))
        else:
            row['status']='NAO_EXECUTADO'
            row['evidence']=''
    counts=Counter(x['status'] for x in inventory)
    # Parameterized cases can create multiple JUnit results for one declared function;
    # counts below are concrete JUnit cases, separate from the inventory count.
    junit_counts=Counter(x['status'] for x in executed)
    summary={'inventory_declared':len(inventory),'junit_executed_cases':len(executed),'junit_result_counts':dict(junit_counts),'inventory_counts':dict(counts),'xml_files':[str(p) for p in xml if p.exists()], 'warning':'Teste declarado não é teste executado. Percentual de cobertura não foi calculado.'}
    (out/'resumo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'rastreabilidade.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['module','risk','path','case','nodeid','status','evidence'])
        writer.writeheader();writer.writerows(inventory)
    rows='\n'.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in ('module','risk','case','status'))+'</tr>' for row in inventory)
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ALECE — Relatório de testes</title><style>body{font:15px/1.55 system-ui;max-width:1200px;margin:auto;padding:24px;color:#183328;background:#f5faf7} table{width:100%;border-collapse:collapse;background:white}td,th{padding:10px;text-align:left;border-bottom:1px solid #cbded2}th{background:#e6f1e9;position:sticky;top:0}td:nth-child(4){font-weight:700} .note{padding:12px;background:#e6f1e9;border-radius:12px}</style><h1>Relatório de testes ALECE</h1><p class="note">Só há aprovação com evidência JUnit. Ausência de execução é NAO_EXECUTADO, nunca aprovado.</p>'''
    page+=f'<p>Funções declaradas: {len(inventory)} · casos JUnit executados: {len(executed)} · JUnit aprovados: {junit_counts["APROVADO"]} · JUnit falhos: {junit_counts["FALHOU"]} · JUnit ignorados: {junit_counts["IGNORADO"]}</p><table><thead><tr><th>Módulo</th><th>Risco</th><th>Caso</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></html>'
    (out/'index.html').write_text(page,encoding='utf-8')
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--out',type=Path,default=Path('test-results/quality'))
    ap.add_argument('--junit',action='append',type=Path,default=[])
    args=ap.parse_args()
    print(json.dumps(generate(args.root.resolve(),args.out,args.junit),ensure_ascii=False,indent=2))
