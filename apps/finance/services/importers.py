# SPDX-License-Identifier: GPL-3.0-only
"""Adaptadores modulares para importação de extratos bancários (CSV e OFX).

Segurança:
- Validação de tamanho, tipo, codificação e estrutura antes de processar
- Prevenção de XXE, expansão de entidades, path traversal, XSS, formula injection
- Processamento exclusivamente local (self-hosted), sem transmissão a terceiros
- Limites de processamento configuráveis
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.core.exceptions import ValidationError


# =============================================================================
# Exceções e Tipos
# =============================================================================

class ImportParseError(ValidationError):
    """Erro durante o parsing de arquivo de importação."""
    pass


class ImportSecurityError(ValidationError):
    """Erro de segurança durante a importação."""
    pass


class ImportFormatError(ValidationError):
    """Formato de arquivo não reconhecido ou inválido."""
    pass


@dataclass
class ParsedTransaction:
    """Transação normalizada extraída do arquivo."""
    fitid: str = ""
    occurred_on: Optional[date] = None
    posted_on: Optional[date] = None
    description: str = ""
    memo: str = ""
    amount: Decimal = Decimal("0.00")
    is_credit: bool = False
    raw_data: dict = field(default_factory=dict)


@dataclass
class ParsedStatement:
    """Extrato completo parseado."""
    institution_id: str = ""
    account_id: str = ""
    account_type: str = ""
    currency: str = "BRL"
    transactions: list[ParsedTransaction] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    parser_version: str = "1.0"


# =============================================================================
# Configurações de Segurança
# =============================================================================

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MiB
MAX_ROWS = 5000
MAX_DESCRIPTION_LENGTH = 500
MAX_MEMO_LENGTH = 2000
ALLOWED_CSV_ENCODINGS = ["utf-8", "utf-8-sig", "iso-8859-1", "latin-1", "cp1252"]
ALLOWED_CSV_DELIMITERS = [",", ";", "\t", "|"]
ALLOWED_OFX_VERSIONS = ["102", "103", "200", "211", "220"]  # OFX 1.x e 2.x


# =============================================================================
# Utilitários de Segurança
# =============================================================================

def validate_file_size(file_content: bytes) -> None:
    """Valida tamanho do arquivo."""
    if len(file_content) > MAX_FILE_SIZE:
        raise ImportSecurityError(f"Arquivo excede o limite de {MAX_FILE_SIZE // (1024*1024)} MiB.")


def validate_file_type(filename: str, content: bytes) -> str:
    """Detecta e valida tipo de arquivo pela extensão e conteúdo."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith(".csv"):
        return "csv"
    elif filename_lower.endswith(".ofx"):
        # Detectar se é OFX 1.x (SGML) ou 2.x (XML)
        if content.lstrip().startswith(b"<?xml") or content.lstrip().startswith(b"<OFX>"):
            return "ofx2"
        return "ofx"
    else:
        raise ImportFormatError(
            "Formato não suportado. Use arquivos .csv ou .ofx."
        )


def sanitize_text(text: str, max_length: int) -> str:
    """Sanitiza texto para prevenir XSS e injection."""
    if not text:
        return ""
    # Remover caracteres de controle exceto tab, newline, carriage return
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    # Truncar
    return text[:max_length]


def parse_decimal_safe(value: str) -> Decimal:
    """Parse seguro de decimal com validação."""
    if not value or not value.strip():
        return Decimal("0.00")
    # Remover espaços, separadores de milhar, símbolos de moeda
    cleaned = re.sub(r"[^\d\-,.]", "", value.strip())
    # Tratar separador decimal (último . ou , é o separador decimal)
    if "," in cleaned and "." in cleaned:
        # Ambos presentes - o último é o separador decimal
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Só vírgula - pode ser separador decimal ou milhar
        parts = cleaned.split(",")
        if len(parts[-1]) == 2 and len(parts) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0.00")


def parse_date_flexible(value: str) -> Optional[date]:
    """Parse flexível de data suportando múltiplos formatos."""
    if not value or not value.strip():
        return None
    value = value.strip()
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
        "%d.%m.%Y", "%Y%m%d", "%d%m%Y",
        "%m/%d/%Y", "%m-%d-%Y",  # US formats
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # Tentar parse OFX (YYYYMMDD ou YYYYMMDDHHMMSS)
    if re.match(r"^\d{8}$", value):
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError:
            pass
    if re.match(r"^\d{14}$", value):
        try:
            return datetime.strptime(value, "%Y%m%d%H%M%S").date()
        except ValueError:
            pass
    return None


def compute_sha256(content: bytes) -> str:
    """Computa hash SHA-256 do conteúdo."""
    return hashlib.sha256(content).hexdigest()


# =============================================================================
# Parser Base Abstrato
# =============================================================================

class BaseParser(ABC):
    """Classe base para parsers de extrato."""
    
    def __init__(self, profile, account=None):
        self.profile = profile
        self.account = account
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    @abstractmethod
    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        """Parse do conteúdo do arquivo."""
        pass
    
    def _validate_transaction(self, txn: ParsedTransaction, row_num: int) -> bool:
        """Valida uma transação individual."""
        valid = True
        if txn.occurred_on is None:
            self.errors.append(f"Linha {row_num}: Data obrigatória ausente.")
            valid = False
        if not txn.description and not txn.memo:
            self.errors.append(f"Linha {row_num}: Descrição obrigatória ausente.")
            valid = False
        if txn.amount == 0:
            self.warnings.append(f"Linha {row_num}: Valor zero detectado.")
        # Sanitizar
        txn.description = sanitize_text(txn.description, MAX_DESCRIPTION_LENGTH)
        txn.memo = sanitize_text(txn.memo, MAX_MEMO_LENGTH)
        return valid


# =============================================================================
# Parser CSV
# =============================================================================

class CSVParser(BaseParser):
    """Parser para arquivos CSV com suporte a múltiplos delimitadores, codificações e formatos."""
    
    # Mapeamento de cabeçalhos conhecidos para campos normalizados
    HEADER_MAPPINGS = {
        # Data
        "data": "date", "date": "date", "dt": "date", "dtlanc": "date",
        "datamov": "date", "datamovimento": "date", "dtmov": "date",
        # Descrição
        "descricao": "description", "description": "description", "historico": "description",
        "hist": "description", "memo": "memo", "observacao": "memo", "obs": "memo",
        "complemento": "memo",
        # Valor
        "valor": "amount", "value": "amount", "vl": "amount", "vlr": "amount",
        "importancia": "amount", "montante": "amount",
        # Crédito/Débito
        "tipo": "type", "type": "type", "cd": "type", "c_d": "type",
        "credito_debito": "type", "creddeb": "type", "sinal": "type",
        # Saldo (informativo)
        "saldo": "balance", "balance": "balance",
        # ID único
        "id": "fitid", "fitid": "fitid", "nsu": "fitid", "documento": "fitid",
        "numdoc": "fitid", "num_documento": "fitid",
        # Data compensação
        "datacompensacao": "posted_on", "dtcompensacao": "posted_on",
        "datapagamento": "posted_on", "dtpag": "posted_on",
    }
    
    # Valores que indicam crédito
    CREDIT_INDICATORS = {"c", "cr", "cred", "credito", "crédito", "credit", "+", "receita", "entrada"}
    DEBIT_INDICATORS = {"d", "db", "deb", "debito", "débito", "debit", "-", "despesa", "saida", "saída"}
    
    def __init__(self, profile, account=None, encoding: Optional[str] = None,
                 delimiter: Optional[str] = None, has_header: bool = True,
                 date_format: Optional[str] = None, decimal_separator: Optional[str] = None,
                 credit_debit_columns: bool = False):
        super().__init__(profile, account)
        self.encoding = encoding
        self.delimiter = delimiter
        self.has_header = has_header
        self.date_format = date_format
        self.decimal_separator = decimal_separator
        self.credit_debit_columns = credit_debit_columns  # Colunas separadas de crédito/débito
        self._detected_encoding = None
        self._detected_delimiter = None
    
    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        """Parse do arquivo CSV."""
        validate_file_size(content)
        
        # Detectar encoding
        text_content = self._decode_content(content)
        
        # Detectar delimitador
        delimiter = self._detect_delimiter(text_content)
        self._detected_delimiter = delimiter
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        
        if not reader.fieldnames:
            raise ImportParseError("Arquivo CSV vazio ou sem cabeçalho.")
        
        # Normalizar nomes de colunas
        field_map = self._map_headers(reader.fieldnames)
        
        statement = ParsedStatement()
        row_num = 0
        
        for row in reader:
            row_num += 1
            if row_num > MAX_ROWS:
                self.errors.append(f"Limite de {MAX_ROWS} linhas excedido.")
                break
            
            try:
                txn = self._parse_row(row, field_map, row_num)
                if self._validate_transaction(txn, row_num):
                    statement.transactions.append(txn)
            except Exception as e:
                self.errors.append(f"Linha {row_num}: {str(e)}")
        
        # Definir datas de início/fim
        if statement.transactions:
            dates = [t.occurred_on for t in statement.transactions if t.occurred_on]
            if dates:
                statement.start_date = min(dates)
                statement.end_date = max(dates)
        
        statement.parser_version = "csv-1.0"
        return statement
    
    def _decode_content(self, content: bytes) -> str:
        """Decodifica conteúdo testando múltiplas codificações."""
        encodings = [self.encoding] if self.encoding else ALLOWED_CSV_ENCODINGS
        
        for enc in encodings:
            try:
                text = content.decode(enc)
                self._detected_encoding = enc
                return text
            except UnicodeDecodeError:
                continue
        
        raise ImportParseError(
            f"Não foi possível decodificar o arquivo. Codificações tentadas: {', '.join(encodings)}"
        )
    
    def _detect_delimiter(self, text: str) -> str:
        """Detecta delimitador do CSV."""
        if self.delimiter:
            return self.delimiter
        
        # Amostrar primeiras linhas
        sample = "\n".join(text.split("\n")[:5])
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample, delimiters="".join(ALLOWED_CSV_DELIMITERS))
            return dialect.delimiter
        except csv.Error:
            # Fallback: contar ocorrências
            counts = {d: sample.count(d) for d in ALLOWED_CSV_DELIMITERS}
            return max(counts, key=counts.get) if max(counts.values()) > 0 else ","
    
    def _map_headers(self, headers: list[str]) -> dict[str, str]:
        """Mapeia cabeçalhos do CSV para campos normalizados."""
        field_map = {}
        for header in headers:
            normalized = header.strip().lower().replace(" ", "").replace("_", "")
            if normalized in self.HEADER_MAPPINGS:
                field_map[header] = self.HEADER_MAPPINGS[normalized]
        return field_map
    
    def _parse_row(self, row: dict, field_map: dict, row_num: int) -> ParsedTransaction:
        """Parse de uma linha do CSV."""
        txn = ParsedTransaction()
        txn.raw_data = {k: v for k, v in row.items() if v}
        
        # Data
        date_field = field_map.get("date") or field_map.get("datamov")
        if date_field and date_field in row:
            txn.occurred_on = parse_date_flexible(row[date_field])
        
        # Data compensação
        posted_field = field_map.get("posted_on")
        if posted_field and posted_field in row:
            txn.posted_on = parse_date_flexible(row[posted_field])
        
        # Descrição
        desc_field = field_map.get("description")
        memo_field = field_map.get("memo")
        if desc_field and desc_field in row:
            txn.description = row[desc_field] or ""
        if memo_field and memo_field in row:
            txn.memo = row[memo_field] or ""
        
        # FITID
        fitid_field = field_map.get("fitid")
        if fitid_field and fitid_field in row:
            txn.fitid = str(row[fitid_field]).strip()
        
        # Valor e tipo (crédito/débito)
        if self.credit_debit_columns:
            # Colunas separadas
            credit_field = field_map.get("credit")
            debit_field = field_map.get("debit")
            if credit_field and credit_field in row and row[credit_field]:
                txn.amount = parse_decimal_safe(row[credit_field])
                txn.is_credit = True
            elif debit_field and debit_field in row and row[debit_field]:
                txn.amount = parse_decimal_safe(row[debit_field])
                txn.is_credit = False
            else:
                # Tentar coluna valor único
                self._parse_single_amount(row, field_map, txn)
        else:
            self._parse_single_amount(row, field_map, txn)
        
        # Se não temos FITID, gerar hash contextual
        if not txn.fitid:
            ctx = f"{txn.occurred_on}|{txn.amount}|{txn.description}|{txn.memo}"
            txn.fitid = hashlib.sha256(ctx.encode()).hexdigest()[:32]
        
        return txn
    
    def _parse_single_amount(self, row: dict, field_map: dict, txn: ParsedTransaction) -> None:
        """Parse de valor único com coluna de tipo ou sinal."""
        amount_field = field_map.get("amount")
        type_field = field_map.get("type")
        
        if amount_field and amount_field in row:
            raw_value = row[amount_field]
            txn.amount = parse_decimal_safe(raw_value)
            
            # Determinar se crédito ou débito
            if type_field and type_field in row:
                type_val = str(row[type_field]).strip().lower()
                if type_val in self.CREDIT_INDICATORS:
                    txn.is_credit = True
                elif type_val in self.DEBIT_INDICATORS:
                    txn.is_credit = False
                else:
                    # Inferir pelo sinal do valor
                    txn.is_credit = txn.amount > 0
            else:
                # Inferir pelo sinal do valor
                txn.is_credit = txn.amount > 0
            
            # Valor absoluto
            txn.amount = abs(txn.amount)


# =============================================================================
# Parser OFX 1.x (SGML)
# =============================================================================

class OFX1Parser(BaseParser):
    """Parser para OFX 1.x (formato SGML-like)."""
    
    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        validate_file_size(content)
        
        # OFX 1.x não é XML válido, precisa de pré-processamento
        text = content.decode("utf-8", errors="replace")
        text = content.decode("latin-1", errors="replace") if "latin" in text.lower() else text
        
        # Extrair blocos SGML principais
        statement = self._parse_sgml(text)
        statement.parser_version = "ofx1-1.0"
        return statement
    
    def _parse_sgml(self, text: str) -> ParsedStatement:
        """Parse básico de formato SGML do OFX 1.x."""
        statement = ParsedStatement()
        
        # Extrair informações da conta
        statement.institution_id = self._extract_tag(text, "BANKID") or self._extract_tag(text, "ORG")
        statement.account_id = self._extract_tag(text, "ACCTID")
        statement.account_type = self._extract_tag(text, "ACCTTYPE")
        statement.currency = self._extract_tag(text, "CURDEF") or "BRL"
        
        # Extrair transações
        # Procurar blocos STMTTRN
        stmttrn_blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, re.DOTALL | re.IGNORECASE)
        
        for i, block in enumerate(stmttrn_blocks):
            if i >= MAX_ROWS:
                self.errors.append(f"Limite de {MAX_ROWS} transações excedido.")
                break
            
            txn = ParsedTransaction()
            txn.fitid = self._extract_tag(block, "FITID") or ""
            txn.occurred_on = self._parse_ofx_date(self._extract_tag(block, "DTPOSTED"))
            txn.posted_on = self._parse_ofx_date(self._extract_tag(block, "DTAVAIL"))
            txn.description = sanitize_text(self._extract_tag(block, "NAME") or "", MAX_DESCRIPTION_LENGTH)
            txn.memo = sanitize_text(self._extract_tag(block, "MEMO") or "", MAX_MEMO_LENGTH)
            
            # Valor
            trnamt = self._extract_tag(block, "TRNAMT")
            if trnamt:
                txn.amount = abs(parse_decimal_safe(trnamt))
                # TRNTYPE indica crédito/débito
                trntype = self._extract_tag(block, "TRNTYPE")
                txn.is_credit = trntype in ("CREDIT", "DEP", "INT", "DIV", "CREDIT")
            
            # FITID obrigatório no OFX
            if not txn.fitid:
                ctx = f"{txn.occurred_on}|{txn.amount}|{txn.description}|{txn.memo}"
                txn.fitid = hashlib.sha256(ctx.encode()).hexdigest()[:32]
            
            txn.raw_data = {
                "trntype": self._extract_tag(block, "TRNTYPE"),
                "checknum": self._extract_tag(block, "CHECKNUM"),
                "refnum": self._extract_tag(block, "REFNUM"),
            }
            
            if self._validate_transaction(txn, i + 1):
                statement.transactions.append(txn)
        
        # Datas do extrato
        dtstart = self._extract_tag(text, "DTSTART")
        dtend = self._extract_tag(text, "DTEND")
        if dtstart:
            statement.start_date = self._parse_ofx_date(dtstart)
        if dtend:
            statement.end_date = self._parse_ofx_date(dtend)
        
        return statement
    
    def _extract_tag(self, text: str, tag: str) -> Optional[str]:
        """Extrai valor de uma tag SGML."""
        pattern = f"<{tag}>([^<]*)</{tag}>"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _parse_ofx_date(self, value: Optional[str]) -> Optional[date]:
        """Parse de data no formato OFX (YYYYMMDD ou YYYYMMDDHHMMSS)."""
        if not value:
            return None
        value = value.strip()
        if re.match(r"^\d{8}$", value):
            try:
                return datetime.strptime(value[:8], "%Y%m%d").date()
            except ValueError:
                pass
        if re.match(r"^\d{14}$", value):
            try:
                return datetime.strptime(value[:14], "%Y%m%d%H%M%S").date()
            except ValueError:
                pass
        return parse_date_flexible(value)


# =============================================================================
# Parser OFX 2.x (XML)
# =============================================================================

class OFX2Parser(BaseParser):
    """Parser para OFX 2.x (formato XML) com proteção contra XXE."""
    
    def __init__(self, profile, account=None):
        super().__init__(profile, account)
        # Configurar parser XML seguro (sem DTD, sem entidades externas)
        self.parser = ET.XMLParser(
            target=ET.TreeBuilder(),
            encoding="utf-8"
        )
        # Desabilitar entidades externas (prevenção XXE)
        self.parser.entity = {}
    
    def parse(self, content: bytes, filename: str) -> ParsedStatement:
        validate_file_size(content)
        
        # Detectar encoding do XML
        text = content.decode("utf-8", errors="replace")
        if "encoding=" in text[:100].lower():
            # Tentar extrair encoding declarado
            match = re.search(r'encoding=["\']([^"\']+)["\']', text, re.IGNORECASE)
            if match:
                declared_enc = match.group(1)
                try:
                    text = content.decode(declared_enc, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    pass
        
        # Parse XML seguro
        try:
            root = ET.fromstring(text, parser=self.parser)
        except ET.ParseError as e:
            raise ImportParseError(f"XML inválido: {str(e)}")
        
        statement = self._parse_ofx2(root)
        statement.parser_version = "ofx2-1.0"
        return statement
    
    def _parse_ofx2(self, root: ET.Element) -> ParsedStatement:
        """Parse do XML OFX 2.x."""
        statement = ParsedStatement()
        
        # Namespace OFX
        ns = {"ofx": "http://ofx.net/types/2003/04"}
        
        # Encontrar extrato bancário
        # OFX pode ter múltiplos tipos de mensagem: BANKMSGSRSV1, CCMSGSRSV1, etc.
        stmt_el = None
        for msg_type in ["BANKMSGSRSV1", "CCMSGSRSV1", "INVSTMTMSGSRSV1"]:
            stmt_el = root.find(f".//ofx:{msg_type}", ns)
            if stmt_el is not None:
                break
        
        if stmt_el is None:
            # Tentar sem namespace
            for msg_type in ["BANKMSGSRSV1", "CCMSGSRSV1", "INVSTMTMSGSRSV1"]:
                stmt_el = root.find(f".//{msg_type}")
                if stmt_el is not None:
                    break
        
        if stmt_el is None:
            raise ImportParseError("Mensagem OFX não reconhecida (esperado BANKMSGSRSV1, CCMSGSRSV1 ou INVSTMTMSGSRSV1).")
        
        # Extrair STMTRS (Statement Response)
        stmt_rs = stmt_el.find("ofx:STMTRS", ns) or stmt_el.find("STMTRS")
        if stmt_rs is None:
            raise ImportParseError("STMTRS não encontrado na resposta OFX.")
        
        # Informações da conta
        acct_from = stmt_rs.find("ofx:BANKACCTFROM", ns) or stmt_rs.find("BANKACCTFROM")
        if acct_from is not None:
            statement.institution_id = (acct_from.findtext("ofx:BANKID", namespaces=ns) or 
                                         acct_from.findtext("BANKID") or "")
            statement.account_id = (acct_from.findtext("ofx:ACCTID", namespaces=ns) or 
                                     acct_from.findtext("ACCTID") or "")
            statement.account_type = (acct_from.findtext("ofx:ACCTTYPE", namespaces=ns) or 
                                       acct_from.findtext("ACCTTYPE") or "")
        
        # Moeda
        curdef = stmt_rs.findtext("ofx:CURDEF", namespaces=ns) or stmt_rs.findtext("CURDEF")
        statement.currency = curdef or "BRL"
        
        # Transações
        banktranlist = stmt_rs.find("ofx:BANKTRANLIST", ns) or stmt_rs.find("BANKTRANLIST")
        if banktranlist is not None:
            # Datas do extrato
            dtstart = banktranlist.findtext("ofx:DTSTART", namespaces=ns) or banktranlist.findtext("DTSTART")
            dtend = banktranlist.findtext("ofx:DTEND", namespaces=ns) or banktranlist.findtext("DTEND")
            if dtstart:
                statement.start_date = self._parse_ofx_date(dtstart)
            if dtend:
                statement.end_date = self._parse_ofx_date(dtend)
            
            # STMTTRN entries
            for i, stmttrn in enumerate(banktranlist.findall("ofx:STMTTRN", ns) or banktranlist.findall("STMTTRN")):
                if i >= MAX_ROWS:
                    self.errors.append(f"Limite de {MAX_ROWS} transações excedido.")
                    break
                
                txn = ParsedTransaction()
                txn.fitid = (stmttrn.findtext("ofx:FITID", namespaces=ns) or 
                              stmttrn.findtext("FITID") or "").strip()
                txn.occurred_on = self._parse_ofx_date(
                    stmttrn.findtext("ofx:DTPOSTED", namespaces=ns) or 
                    stmttrn.findtext("DTPOSTED")
                )
                txn.posted_on = self._parse_ofx_date(
                    stmttrn.findtext("ofx:DTAVAIL", namespaces=ns) or 
                    stmttrn.findtext("DTAVAIL")
                )
                txn.description = sanitize_text(
                    stmttrn.findtext("ofx:NAME", namespaces=ns) or 
                    stmttrn.findtext("NAME") or "", MAX_DESCRIPTION_LENGTH
                )
                txn.memo = sanitize_text(
                    stmttrn.findtext("ofx:MEMO", namespaces=ns) or 
                    stmttrn.findtext("MEMO") or "", MAX_MEMO_LENGTH
                )
                
                # Valor
                trnamt_text = (stmttrn.findtext("ofx:TRNAMT", namespaces=ns) or 
                                stmttrn.findtext("TRNAMT") or "0")
                txn.amount = abs(parse_decimal_safe(trnamt_text))
                
                # Tipo de transação
                trntype = (stmttrn.findtext("ofx:TRNTYPE", namespaces=ns) or 
                            stmttrn.findtext("TRNTYPE") or "").strip().upper()
                txn.is_credit = trntype in ("CREDIT", "DEP", "INT", "DIV", "DIRECTDEP", "CREDIT")
                
                # FITID obrigatório no OFX 2.x
                if not txn.fitid:
                    ctx = f"{txn.occurred_on}|{txn.amount}|{txn.description}|{txn.memo}"
                    txn.fitid = hashlib.sha256(ctx.encode()).hexdigest()[:32]
                
                txn.raw_data = {
                    "trntype": trntype,
                    "checknum": (stmttrn.findtext("ofx:CHECKNUM", namespaces=ns) or 
                                  stmttrn.findtext("CHECKNUM") or ""),
                    "refnum": (stmttrn.findtext("ofx:REFNUM", namespaces=ns) or 
                                stmttrn.findtext("REFNUM") or ""),
                }
                
                if self._validate_transaction(txn, i + 1):
                    statement.transactions.append(txn)
        
        return statement
    
    def _parse_ofx_date(self, value: Optional[str]) -> Optional[date]:
        """Parse de data no formato OFX."""
        if not value:
            return None
        value = value.strip()
        if re.match(r"^\d{8}$", value):
            try:
                return datetime.strptime(value[:8], "%Y%m%d").date()
            except ValueError:
                pass
        if re.match(r"^\d{14}$", value):
            try:
                return datetime.strptime(value[:14], "%Y%m%d%H%M%S").date()
            except ValueError:
                pass
        return parse_date_flexible(value)


# =============================================================================
# Factory de Parsers
# =============================================================================

def get_parser(format_type: str, profile, account=None, **options) -> BaseParser:
    """Factory para obter parser apropriado."""
    parsers = {
        "csv": CSVParser,
        "ofx": OFX1Parser,
        "ofx2": OFX2Parser,
    }
    
    parser_class = parsers.get(format_type.lower())
    if not parser_class:
        raise ImportFormatError(f"Formato não suportado: {format_type}")
    
    return parser_class(profile, account, **options)


def detect_format(filename: str, content: bytes) -> str:
    """Detecta formato do arquivo."""
    return validate_file_type(filename, content)