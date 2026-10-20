#!/usr/bin/env python3
"""Opt-in edit/save/reopen checks on downloaded, unfilled corpus forms.

Requires pikepdf. Set XFA_QA_CORPUS=corpus/files and optionally PDFXFA to a
sanitized binary. XFA_QA_OUTPUT retains PDFs, logs and results.json.
"""
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

try:
    import pikepdf
except ImportError:
    pikepdf = None


def field_signature(field):
    value = str(field.get('/V', ''))
    if re.fullmatch(r'/f\d+', value):
        value = 'on'
    # XFA node serials and radio on-state names change on restoration.
    # Compare answers, selected children, labels and field properties instead.
    return (str(field.get('/FT', '')), str(field.get('/TU', '')), value,
            int(field.get('/Ff', 0)), str(field.get('/I', '')),
            None if '/AS' not in field else str(field.AS) != '/Off',
            tuple(field_signature(kid) for kid in field.get('/Kids', [])))


def signature(path):
    with pikepdf.open(path) as doc:
        fields = doc.Root.get('/AcroForm', {}).get('/Fields', [])
        result = len(doc.pages), tuple(field_signature(f) for f in fields)
    text = subprocess.check_output(['pdftotext', '-layout', str(path), '-'], stderr=subprocess.DEVNULL)
    return *result, text


def edits(path):
    text_edits, choices = [], []
    with pikepdf.open(path) as doc:
        for field in doc.Root.get('/AcroForm', {}).get('/Fields', []):
            if int(field.get('/Ff', 0)) & 1:
                continue
            name = str(field.get('/T', ''))
            kind = str(field.get('/FT', ''))
            label = str(field.get('/TU', '')).lower()
            if kind == '/Tx' and len(text_edits) < 3:
                if re.search(r'number of|count|copies|dependants|children', label):
                    continue
                if re.search(r'date|yyyy|birth', label):
                    value = '2000-01-02'
                elif re.search(r'number|amount|income|phone|social insurance|\bsin\b|\byear\b', label):
                    value = '123'
                elif 'email' in label or 'e-mail' in label:
                    value = 'qa@example.org'
                else:
                    value = 'Alex Example'
                limit = int(field.get('/MaxLen', 0))
                text_edits.append((name, value[:limit] if limit > 0 else value))
            elif kind == '/Ch' and not choices:
                for option in field.get('/Opt', []):
                    value = str(option[0] if isinstance(option, pikepdf.Array) else option)
                    if value and value != str(field.get('/V', '')):
                        choices.append((name, value))
                        break
    # Choices can change which fields exist, so change the choice last.
    return text_edits + choices


def expected_recalculation(source, before, after):
    # This template unconditionally assigns the current year to its two
    # globally bound Instalment fields in its layout-ready script. It runs
    # again on reopening. Permit only that exact, author-requested change.
    if source.name != 'inns3-fill-19e.pdf' or before[0] != after[0] or len(before[1]) != len(after[1]):
        return False
    year = str(datetime.datetime.now().year)
    changed = 0
    for old, new in zip(before[1], after[1]):
        if old != new:
            if ('Instalment payment for.' not in old[1] or new[2] != year
                    or old[:2] + old[3:] != new[:2] + new[3:]):
                return False
            changed += 1
    def without_year(text):
        return re.sub(r'\b' + year + r'\b', '', text.decode()).split()
    return changed == 2 and without_year(before[2]) == without_year(after[2])


@unittest.skipUnless(os.environ.get('XFA_QA_CORPUS'), 'set XFA_QA_CORPUS to enable the corpus sweep')
class CorpusTests(unittest.TestCase):
    def test_edit_save_reopen(self):
        if pikepdf is None:
            self.fail('The corpus check requires pikepdf')
        binary = str(Path(os.environ.get('PDFXFA', '_install/bin/pdfxfa')).resolve())
        sources = sorted(Path(os.environ['XFA_QA_CORPUS']).resolve().glob('*.pdf'))
        self.assertTrue(sources, 'No corpus PDFs found')
        with tempfile.TemporaryDirectory(prefix='xfa-corpus-') as temp:
            out = Path(os.environ.get('XFA_QA_OUTPUT', temp)).resolve()
            out.mkdir(parents=True, exist_ok=True)

            def check(source):
                record = {'form': source.name}
                paths = [out / (source.stem + suffix) for suffix in ['-initial.pdf', '-edited.pdf', '-reopened.pdf']]
                try:
                    with (out / (source.stem + '.log')).open('wb') as log:
                        def invoke(src, dest, *actions):
                            subprocess.run([binary, '-log', *actions, str(src), str(dest)],
                                           stdout=log, stderr=log, timeout=90, check=True)
                        invoke(source, paths[0])
                        actions = edits(paths[0])
                        args = [arg for name, value in actions for arg in ['-set-field', name + '=' + value]]
                        invoke(source, paths[1], '-preserve-xfa', *args)
                        invoke(paths[1], paths[2])
                    before, after = signature(paths[1]), signature(paths[2])
                    record.update(actions=len(actions), pages=before[0], fields=len(before[1]),
                                  pages_equal=before[0] == after[0], values_equal=before[1] == after[1],
                                  text_equal=before[2] == after[2])
                    record['expected_recalculation'] = expected_recalculation(source, before, after)
                    log = (out / (source.stem + '.log')).read_text(errors='replace')
                    record['sanitizer'] = any(s in log for s in ['ERROR: AddressSanitizer', 'runtime error:', 'ERROR: LeakSanitizer'])
                except Exception as exc:
                    record['failure'] = str(exc)
                return record

            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                for result in pool.map(check, sources):
                    results.append(result)
                    (out / 'results.json').write_text(json.dumps(results, indent=2))
                    print(f'{len(results)}/{len(sources)} {result}', flush=True)
                    with self.subTest(form=result['form']):
                        self.assertNotIn('failure', result)
                        self.assertFalse(result['sanitizer'])
                        self.assertTrue(result['pages_equal'])
                        self.assertTrue(result['values_equal'] or result['expected_recalculation'])
                        self.assertTrue(result['text_equal'] or result['expected_recalculation'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
