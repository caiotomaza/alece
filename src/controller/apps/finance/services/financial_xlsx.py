# SPDX-License-Identifier: GPL-3.0-only
"""Relatório XLSX legível gerado sem dependências adicionais ao container.

O XLSX é exclusivamente uma visualização dos dados financeiros do arquivo JSON.
Células não contêm fórmulas, links, macros nem dados de usuários/permissões.
"""
from __future__ import annotations
from io import BytesIO
import re
from xml.sax.saxutils import escape, quoteattr
import zipfile

from django.db import models
from apps.finance.services.financial_transfer import MODEL_ORDER, MODEL_CLASSES, _fields


def _letters(col):
    value = ''
    while col:
        col, mod = divmod(col - 1, 26)
        value = chr(65 + mod) + value
    return value


def _cell(value, coordinate, is_header=False, is_numeric=False):
    if value is None:
        return f'<c r="{coordinate}"/>'
    if is_numeric and not isinstance(value, bool):
        try:
            value = str(value)
            float(value)
            return f'<c r="{coordinate}" s="2"><v>{escape(value)}</v></c>'
        except (ValueError, OverflowError):
            pass
    text = str(value)
    # XML 1.0 rejects control characters; no formulas are emitted.
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    style = ' s="1"' if is_header else ''
    return f'<c r="{coordinate}" t="inlineStr"{style}><is><t>{escape(text)}</t></is></c>'


def render_xlsx(payload):
    buffer = BytesIO()
    names = ['LEIA_ME'] + list(MODEL_ORDER)
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>''' + ''.join(
    f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    for i in range(1,len(names)+1)) + '</Types>')
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        z.writestr('xl/_rels/workbook.xml.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">''' + ''.join(
    f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
    for i in range(1,len(names)+1)) + f'<Relationship Id="rId{len(names)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' + '</Relationships>')
        z.writestr('xl/workbook.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>''' + ''.join(
    f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>' for i,name in enumerate(names, 1)) + '</sheets></workbook>')
        z.writestr('xl/styles.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF146C43"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>
</styleSheet>''')
        note_rows = [
            ['ALECE | Arquivo de leitura financeira'],
            ['Uso', 'Consulta de dados; não é arquivo de restauração'],
            ['Importação', 'Use sempre o ZIP completo contendo financeiro.json'],
            ['Conteúdo', 'Perfis e entidades financeiras sem usuários, senhas, permissões ou logs'],
            ['Segurança', 'Dados financeiros sensíveis: mantenha armazenado em local seguro'],
        ]
        for number, name in enumerate(names, 1):
            if name == 'LEIA_ME':
                fields = None
                rows = note_rows
            else:
                fields = [MODEL_CLASSES[name]._meta.pk] + _fields(name)
                rows = [[f.name for f in fields]]
                for item in payload['tables'][name]:
                    rows.append([item[f.name] for f in fields])
            widths = ''.join(f'<col min="{i}" max="{i}" width="{28 if i == 1 else 21}" customWidth="1"/>' for i in range(1,max(3,len(rows[0]))+1))
            lines = []
            for rindex, cells in enumerate(rows,1):
                encoded = []
                for cindex, value in enumerate(cells,1):
                    numeric = (fields is not None and rindex>1 and isinstance(fields[cindex-1],
                                    (models.DecimalField, models.IntegerField, models.FloatField)))
                    encoded.append(_cell(value,f'{_letters(cindex)}{rindex}', is_header=rindex==1, is_numeric=numeric))
                lines.append(f'<row r="{rindex}">'+''.join(encoded)+'</row>')
            maxcol = _letters(max(len(row) for row in rows))
            z.writestr(f'xl/worksheets/sheet{number}.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'''+
                f'<dimension ref="A1:{maxcol}{len(rows)}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+
                f'<cols>{widths}</cols><sheetData>'+''.join(lines)+'</sheetData></worksheet>')
    return buffer.getvalue()
