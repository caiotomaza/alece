# SPDX-License-Identifier: GPL-3.0-only
"""Compare execuções REAIS equivalentes. Não promove baseline automaticamente."""
import argparse
import html
import json
from pathlib import Path
from scripts.performance.metrics import compare, read_run


def main():
    parser = argparse.ArgumentParser(description="Comparação local de desempenho em laboratório")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = compare(read_run(args.before), read_run(args.after))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".html":
        rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in
            (name, entry["before"], entry["after"], entry["delta"])) + "</tr>"
            for name, entry in report["metrics"].items()
        )
        path.write_text("<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
                        "<title>ALECE · Comparação de laboratório</title>"
                        "<h1>Comparação de laboratório</h1><p>Não são métricas de usuários reais.</p>"
                        "<table border='1'><thead><tr><th>Métrica</th><th>Antes</th>"
                        "<th>Depois</th><th>Variação</th></tr></thead><tbody>" + rows +
                        "</tbody></table></html>", encoding="utf-8")
    else:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
