#!/usr/bin/env python3
"""Render a standalone PDF from an ADT job's evidence registers; never infer passes."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path


def load(path, field):
    if not path.is_file():
        return []
    value = json.loads(path.read_text(encoding='utf-8'))
    return value[field]


def build(job, out, font=None, font_bold=None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    import reportlab
    config = json.loads((job / 'job.json').read_text(encoding='utf-8'))
    issues = load(job / 'reports/issues.json', 'issues')
    notes = load(job / 'reports/reviewer-notes.json', 'notes')
    checks = load(job / 'reports/validation.json', 'checks')
    fonts = Path(reportlab.__file__).parent / 'fonts'
    regular = Path(font) if font else fonts / 'Vera.ttf'
    bold = Path(font_bold) if font_bold else (regular if font else fonts / 'VeraBd.ttf')
    pdfmetrics.registerFont(TTFont('ADTReport', str(regular)))
    pdfmetrics.registerFont(TTFont('ADTReportBold', str(bold)))
    styles = getSampleStyleSheet()
    for key in ['Title', 'Heading1', 'Heading2', 'BodyText']:
        styles[key].fontName = 'ADTReportBold' if key != 'BodyText' else 'ADTReport'
        styles[key].alignment = TA_LEFT
        styles[key].textColor = colors.HexColor('#182c3b')
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 14
    styles['BodyText'].spaceAfter = 7
    styles.add(ParagraphStyle('Detail', parent=styles['BodyText'], fontSize=8, leading=12))
    story = []
    def para(value, style='BodyText'):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        story.append(Paragraph(html.escape(str(value)).replace('\n', '<br/>'), styles[style]))
    def field(label, value):
        if value is not None and value != '' and value != []:
            para(f'{label}: {value}', 'Detail')
    para('ADT Review and Repair Report', 'Title')
    para('Generated ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
    field('Tool version', config.get('tool_version', 'unrecorded'))
    field('Book', config['input']['pdf'].replace('\\', '/').split('/')[-1])
    field('Source PDF SHA-256', config['input'].get('pdf_sha256', 'unrecorded'))
    field('Physical PDF pages', config.get('physical_pdf_pages', []))
    field('Languages', ', '.join(config.get('languages', [])))
    field('Mode / recorded stage', f"{config.get('mode', 'unknown')} / {config.get('stage', 'unknown')}")
    para(f'{len(issues)} recorded issues; {len(notes)} actionable reviewer notes; {len(checks)} validation checks.')
    para('This report summarizes recorded evidence. Missing records and checks not run are not passes. Automated checks alone do not establish full accessibility conformance.')
    for title, rows, empty in [
        ('Issues and actions', issues, 'No issues recorded. Audit completeness has not been established by this fact.'),
        ('Teacher and reviewer feedback', notes, 'No actionable notes recorded. See supplied note files and ingestion coverage.'),
        ('Validation and limitations', checks, 'No validation checks recorded. Validation is not established.'),
    ]:
        para(title, 'Heading1')
        if not rows:
            para(empty)
        for row in rows:
            name = row.get('summary', row.get('name', row.get('comment', 'Untitled record')))
            para(f"{row.get('id', '')} {name}", 'Heading2')
            for key in ['category', 'severity', 'source', 'source_location', 'status', 'scope', 'pdf_pages',
                        'sections', 'languages', 'priority', 'evidence', 'action', 'verification', 'disposition',
                        'limitations', 'note_ids', 'issue_ids']:
                field(key.replace('_', ' ').capitalize(), row.get(key))
            story.append(Spacer(1, 5))
    supplied = config.get('notes', [])
    para('Supplied note files', 'Heading1')
    if not supplied:
        para('No teacher or reviewer note files supplied. Pasted notes, if any, should be identified in the feedback register.')
    for item in supplied:
        para(item['copy'], 'Detail')
        field('SHA-256', item['sha256'])
    summary = job / 'reports/report-summary.md'
    if summary.is_file():
        para('Coverage, follow-ups and recommendations', 'Heading1')
        for block in summary.read_text(encoding='utf-8').split('\n\n'):
            if block.strip():
                para(block.strip())
    else:
        para('No additional coverage or follow-up summary recorded. Consult the source map and validation evidence before accepting the repair.')
    out.parent.mkdir(parents=True, exist_ok=True)
    def footer(canvas, doc):
        canvas.setFont('ADTReport', 8)
        canvas.drawString(42, 25, 'ADT Repair | evidence report')
        canvas.drawRightString(A4[0] - 42, 25, str(doc.page))
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=42, rightMargin=42,
                            topMargin=40, bottomMargin=43, title='ADT Review and Repair Report')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--font', type=Path)
    parser.add_argument('--font-bold', type=Path)
    args = parser.parse_args()
    print(build(args.job, args.out, args.font, args.font_bold))


if __name__ == '__main__':
    main()
