#!/usr/bin/env python3
"""Black-box XFA CLI regressions using synthetic PDFs only.

PDFXFA=/path/to/pdfxfa python3 tools/qa/test_core.py
Set XFA_QA_OUTPUT to retain fixtures, results and stderr for investigation.
"""
import os
import re
from pathlib import Path
import resource
import subprocess
import tempfile
import unittest


def pdf(xdp, state=None, state_object=None):
    if isinstance(xdp, str):
        xdp = xdp.encode()
    extra = b" /PopplerXFAState 5 0 R" if state is not None else b""
    if state_object is not None:
        extra = b" /PopplerXFAState " + state_object
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /NeedsRendering true /AcroForm << /Fields [] /XFA 4 0 R" + extra + b" >> >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
        b"<< /Length %d >>\nstream\n" % len(xdp) + xdp + b"\nendstream",
    ]
    if state is not None:
        objects.append(b"<< /Length %d >>\nstream\n" % len(state) + state + b"\nendstream")
    result = bytearray(b"%PDF-1.7\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(b"%d 0 obj\n" % number + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        result.extend(b"%010d 00000 n \n" % offset)
    result.extend(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return bytes(result)


def template(content="", script=""):
    return ('<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">'
            '<template xmlns="http://www.xfa.org/schema/xfa-template/3.3/">'
            '<subform name="form1" layout="tb">'
            '<pageSet><pageArea name="Page1">'
            '<contentArea x="0.5in" y="0.5in" w="7in" h="10in"/>'
            '<medium short="8.5in" long="11in"/></pageArea></pageSet>'
            '<draw w="5in" h="0.4in"><value><text>Sentinel</text></value></draw>'
            + content + script + '</subform></template></xdp:xdp>')


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = str(Path(os.environ.get('PDFXFA', '_install/bin/pdfxfa')).resolve())
        cls.temp = tempfile.TemporaryDirectory(prefix='xfa-core-')
        cls.out = Path(os.environ.get('XFA_QA_OUTPUT', cls.temp.name)).resolve()
        cls.out.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def invoke(self, data, *actions, expected=0, timeout=15, target=None):
        name = self.id().rsplit('.', 1)[-1]
        source = self.out / f'{name}-in.pdf'
        output = Path(target) if target is not None else self.out / f'{name}-out.pdf'
        source.write_bytes(data)
        result = subprocess.run([self.binary, '-log', *actions, str(source), str(output)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        (self.out / f'{name}.log').write_bytes(result.stderr)
        self.assertEqual(result.returncode, expected, result.stderr.decode(errors='replace')[-2500:])
        if expected == 0 and target is None:
            self.assertTrue(output.read_bytes().startswith(b'%PDF-'))
        return output, result.stderr.decode(errors='replace')

    def test_render(self):
        self.invoke(pdf(template()))

    def test_invalid_xml(self):
        for xml in ['', '<', '<subform>', '<a></b>', '<template a=>', '<!--', '<a><![CDATA[']:
            with self.subTest(xml=xml):
                self.invoke(pdf(xml), expected=2)

    def test_deep_xml(self):
        self.invoke(pdf('<n>' * 6000 + '</n>' * 6000), expected=2)

    def test_saved_state_wrong_type(self):
        for value in [b'123', b'<<>>', b'(invalid)', b'[]']:
            with self.subTest(value=value):
                self.invoke(pdf(template(), state_object=value), expected=2)

    def test_invalid_saved_states(self):
        for state in [b'', b'<state/>', b'<state version="999"><form/></state>',
                      b'<state version="1"><form/></state>',
                      b'<state version="1"><form><subform poppler:proto="garbage"/></form></state>']:
            with self.subTest(state=state):
                self.invoke(pdf(template(), state=state), expected=2)

    def test_unknown_field(self):
        self.invoke(pdf(template()), '-set', 'missing=value', expected=3)

    def test_unknown_button(self):
        self.invoke(pdf(template()), '-click', 'missing', expected=3)

    def test_unknown_export_field(self):
        self.invoke(pdf(template()), '-set-field', 'missing=value', expected=3)

    def test_print_and_live_are_exclusive(self):
        self.invoke(pdf(template()), '-print', '-preserve-xfa', expected=99)

    def test_output_directory(self):
        self.invoke(pdf(template()), expected=1, target=self.out)

    @unittest.skipUnless(os.environ.get('XFA_QA_DEV_FULL') == '1', 'enable /dev/full outside the filesystem sandbox')
    def test_output_close_error(self):
        self.invoke(pdf(template()), expected=1, target='/dev/full')

    def test_huge_formcalc_nesting(self):
        script = '<field name="total"><ui><textEdit/></ui><calculate><script>' + '(' * 12000 + '1' + ')' * 12000 + '</script></calculate></field>'
        _, log = self.invoke(pdf(template(script)), timeout=15)
        self.assertIn('FormCalc', log)

    def test_deep_script_tree_no_overflow(self):
        # A script builds a node tree far deeper than the parser's limit, then
        # serializes it. The recursive walkers must bound their own depth so
        # this cannot overflow the stack. The child runs with a small stack so
        # a regression crashes deterministically instead of depending on how
        # deep the machine's default stack lets the walk go.
        js = ('var root = xfa.datasets.createNode("dataGroup","deep"); var cur=root;'
              'for (var i=0;i<6000;i=i+1){var c=xfa.datasets.createNode("dataGroup","n");'
              'cur.nodes.append(c);cur=c;}'
              'xfa.host.messageBox(String(root.saveXML().length));')
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  '<![CDATA[' + js + ']]></script></event>')
        name = self.id().rsplit('.', 1)[-1]
        source = self.out / f'{name}-in.pdf'
        source.write_bytes(pdf(template(script=script)))
        output = self.out / f'{name}-out.pdf'
        _, hard = resource.getrlimit(resource.RLIMIT_STACK)

        def small_stack():
            resource.setrlimit(resource.RLIMIT_STACK, (1024 * 1024, hard))

        result = subprocess.run([self.binary, '-log', str(source), str(output)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=30, preexec_fn=small_stack)
        (self.out / f'{name}.log').write_bytes(result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace')[-2000:])

    def test_deep_form_tree_data_binding(self):
        # Binding a field of a deep script-built form tree to data, and
        # setting a global field, walk the tree; neither may overflow.
        js = ('var cur = xfa.resolveNode("form1");'
              'for (var i=0;i<6000;i=i+1){var s=xfa.form.createNode("subform","s");cur.nodes.append(s);cur=s;}'
              'var f = xfa.form.createNode("field","leaf"); cur.nodes.append(f); f.rawValue = "x";'
              'var d = f.dataNode; g.rawValue = "shared";'
              'xfa.host.messageBox("ok " + (d === null ? "null" : d.className));')
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  '<![CDATA[' + js + ']]></script></event>')
        content = ('<field name="g" w="2in" h="0.3in"><ui><textEdit/></ui><bind match="global"/></field>'
                   '<field name="g" w="2in" h="0.3in"><ui><textEdit/></ui><bind match="global"/></field>')
        name = self.id().rsplit('.', 1)[-1]
        source = self.out / f'{name}-in.pdf'
        source.write_bytes(pdf(template(content, script)))
        output = self.out / f'{name}-out.pdf'
        _, hard = resource.getrlimit(resource.RLIMIT_STACK)

        def small_stack():
            resource.setrlimit(resource.RLIMIT_STACK, (1024 * 1024, hard))

        result = subprocess.run([self.binary, '-log', str(source), str(output)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=60, preexec_fn=small_stack)
        (self.out / f'{name}.log').write_bytes(result.stderr)
        log = result.stderr.decode(errors='replace')
        self.assertEqual(result.returncode, 0, log[-2000:])
        self.assertIn('ok ', log)

    def words(self, output):
        # Word boxes in points, top-left origin: {text: (x0, y0, x1, y1)}.
        html = subprocess.check_output(['pdftotext', '-bbox', str(output), '-']).decode()
        return {m[5]: tuple(float(v) for v in m.groups()[:4]) for m in re.finditer(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', html)}

    def dark_box(self, output, top):
        # Bounding box of the dark pixels of page 1 below y = top, at 72 dpi.
        pgm = subprocess.check_output(['pdftoppm', '-r', '72', '-gray', '-f', '1', '-l', '1', str(output)])
        header = pgm.split(b'\n', 3)
        width, height = (int(v) for v in header[1].split())
        pixels = header[3]
        xs, ys = [], []
        for y in range(int(top), height):
            row = pixels[y * width:(y + 1) * width]
            for x, v in enumerate(row):
                if v < 200:
                    xs.append(x)
                    ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def test_rotated_line(self):
        # Designer draws horizontal rules as vertical lines turned a quarter
        # counterclockwise about their top left corner; drawn unturned they
        # ran down the page across other content.
        content = ('<subform w="7in" h="3in"><draw x="1in" y="1in" w="0in" h="2in" rotate="90">'
                   '<value><line><edge thickness="1pt"/></line></value></draw></subform>')
        output, _ = self.invoke(pdf(template(content)))
        top = (0.5 + 0.4) * 72  # below the sentinel
        box = self.dark_box(output, top + 2)
        self.assertIsNotNone(box)
        x0, y0, x1, y1 = box
        self.assertLess(y1 - y0, 4, box)
        self.assertAlmostEqual(x0, 1.5 * 72, delta=2)
        self.assertAlmostEqual(x1, 3.5 * 72, delta=2)
        self.assertAlmostEqual(y0, top + 72, delta=2)

    def test_rotated_text(self):
        # Turned text reads bottom to top in the box it turns into, and a
        # turned box takes that room in a flowed container.
        content = ('<draw w="2in" h="0.3in" rotate="90"><value><text>Turned</text></value></draw>'
                   '<draw w="2in" h="0.3in"><value><text>After</text></value></draw>')
        output, _ = self.invoke(pdf(template(content)))
        words = self.words(output)
        x0, y0, x1, y1 = words['Turned']
        self.assertGreater(y1 - y0, x1 - x0)
        top = (0.5 + 0.4) * 72
        self.assertGreaterEqual(y0, top - 1)
        self.assertLessEqual(y1, top + 2 * 72 + 1)
        self.assertLessEqual(x1, 0.5 * 72 + 0.3 * 72 + 1)
        self.assertGreaterEqual(words['After'][1], top + 2 * 72 - 1)

    def test_space_above_first_paragraph(self):
        # Space above the first paragraph is kept when drawn, as measured
        # and as Acrobat shows it.
        content = ('<subform w="7in" h="2in">'
                   '<draw x="0in" y="0in" w="2in" h="1in"><value><text>Plain</text></value></draw>'
                   '<draw x="3in" y="0in" w="2in" h="1in"><para spaceAbove="20pt"/>'
                   '<value><text>Spaced</text></value></draw></subform>')
        output, _ = self.invoke(pdf(template(content)))
        words = self.words(output)
        self.assertAlmostEqual(words['Spaced'][1] - words['Plain'][1], 20, delta=0.5)

    def test_field_with_default_ui(self):
        self.invoke(pdf(template('<field name="default"><value><text>Default widget</text></value></field>')))

    def test_script_deadline(self):
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  'while (true) {}' '</script></event>')
        _, log = self.invoke(pdf(template(script=script)), timeout=12)
        self.assertIn('interrupted', log)

    def test_live_roundtrips(self):
        content = ('<field name="name" w="4in" h="0.4in"><ui><textEdit/></ui>'
                   '<value><text>initial</text></value>'
                   '<event activity="initialize"><script contentType="application/x-javascript">'
                   'this.rawValue="reset";</script></event></field>')
        output, _ = self.invoke(pdf(template(content)), '-set', 'name=Roundtrip answer', '-preserve-xfa')
        for _ in range(10):
            data = output.read_bytes()
            output, _ = self.invoke(data, '-preserve-xfa')
        output, _ = self.invoke(output.read_bytes())
        text = subprocess.check_output(['pdftotext', str(output), '-']).decode()
        self.assertIn('Roundtrip answer', text)
        self.assertNotIn('reset', text)

    def test_change_event_input_filters(self):
        # Apply the actual edited span, preserving unchanged characters.
        # These patterns occur in the corpus's shared input validators.
        cases = [
            ('ab', 'abc', 'xfa.event.change = xfa.event.change.toUpperCase();', 'abC'),
            ('123', '123x', 'if (/[^0-9]/.test(xfa.event.change)) xfa.event.change = "";', '123'),
            ('123', '12', '', '12'),
            ('keep', 'replace', 'xfa.event.cancelAction = true;', 'keep'),
            ('keep', 'replace', 'event.rc = false;', 'keep'),
            ('é中', 'é中a', 'xfa.event.change = xfa.event.change.toUpperCase();', 'é中A'),
        ]
        for initial, entered, script, expected in cases:
            with self.subTest(initial=initial, entered=entered, expected=expected):
                content = ('<field name="edit" w="4in" h="0.4in"><ui><textEdit/></ui>'
                           '<value><text>' + initial + '</text></value>'
                           '<event activity="change"><script contentType="application/x-javascript">'
                           '<![CDATA[' + script + ']]></script></event></field>')
                output, _ = self.invoke(pdf(template(content)), '-set', 'edit=' + entered)
                text = subprocess.check_output(['pdftotext', str(output), '-']).decode()
                self.assertIn(expected, text)
                if expected != entered:
                    self.assertNotIn(entered, text)

    def test_unicode_widget_appearances(self):
        names = 'Łukasz Иван Ελληνικά 中文'
        for angle in [0, 90, 180, 270]:
            with self.subTest(rotation=angle):
                content = (f'<field name="name" w="4in" h="0.5in" rotate="{angle}">'
                           '<ui><textEdit/></ui></field>')
                output, _ = self.invoke(pdf(template(content)), '-set', 'name=' + names, '-preserve-xfa')
                for cycle in range(3):
                    text = subprocess.check_output(['pdftotext', str(output), '-']).decode()
                    for name in names.split():
                        self.assertIn(name, text, f'cycle {cycle}')
                    output, _ = self.invoke(output.read_bytes(), '-preserve-xfa')

    def test_choice_change_can_cancel(self):
        content = ('<field name="choice" w="4in" h="0.4in"><ui><choiceList/></ui>'
                   '<items><text>Alpha</text><text>Beta</text></items>'
                   '<value><text>Alpha</text></value><event activity="change">'
                   '<script contentType="application/x-javascript">xfa.event.cancelAction=true;</script>'
                   '</event></field>')
        output, _ = self.invoke(pdf(template(content)), '-set', 'choice=Beta')
        text = subprocess.check_output(['pdftotext', str(output), '-']).decode()
        self.assertIn('Alpha', text)
        self.assertNotIn('Beta', text)

    def test_exported_field_in_unnamed_subform(self):
        content = ('<subform name="header"/>'
                   '<subform><field name="name" w="4in" h="0.4in"><ui><textEdit/></ui>'
                   '</field></subform>')
        source = pdf(template(content))
        output, _ = self.invoke(source)
        match = re.search(rb'/T\s+\((xfa[0-9]+)\)', output.read_bytes())
        self.assertIsNotNone(match)
        output, _ = self.invoke(source, '-set-field', match[1].decode() + '=Answer retained')
        text = subprocess.check_output(['pdftotext', str(output), '-']).decode()
        self.assertIn('Answer retained', text)

    def test_script_tree_rejects_cycles(self):
        js = ('var a=xfa.form.createNode("subform","a");'
              'var b=xfa.form.createNode("subform","b");var blocked=0;'
              'try {a.nodes.append(a);} catch(e) {blocked++;}'
              'a.nodes.append(b);'
              'try {b.nodes.append(a);} catch(e) {blocked++;}'
              'xfa.host.messageBox("cycles="+blocked);')
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  '<![CDATA[' + js + ']]></script></event>')
        _, log = self.invoke(pdf(template(script=script)))
        self.assertIn('cycles=2', log)

    def test_script_locals_shadow_fields(self):
        content = '<field name="s"><ui><textEdit/></ui><value><text>original</text></value></field>'
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  'var s=7; xfa.host.messageBox("local="+s+" field="+this.s.rawValue);'
                  '</script></event>')
        _, log = self.invoke(pdf(template(content, script)))
        self.assertIn('local=7 field=original', log)

    def test_som_expression_roundtrips_unnamed_container(self):
        content = ('<subform name="header"/><subform><field name="name"><ui><textEdit/></ui>'
                   '<event activity="initialize"><script contentType="application/x-javascript">'
                   'xfa.host.messageBox("som="+(xfa.resolveNode(this.somExpression)===this));'
                   '</script></event></field></subform>')
        _, log = self.invoke(pdf(template(content)))
        self.assertIn('som=true', log)

    def test_resolve_instance_manager_paths(self):
        content = ('<subform name="Group" layout="tb"><subform name="Row"><occur min="1" max="3"/>'
                   '<field name="v"><ui><textEdit/></ui></field></subform></subform>')
        script = ('<event activity="docReady"><script contentType="application/x-javascript">'
                  'var manager=Group.resolveNode("Group._Row");manager.addInstance();'
                  'xfa.host.messageBox("rows="+manager.count+" direct="+Group.resolveNode("_Row").count'
                  '+" global="+xfa.resolveNode("Group._Row").count);'
                  '</script></event>')
        _, log = self.invoke(pdf(template(content, script)))
        self.assertIn('rows=2 direct=2 global=2', log)


if __name__ == '__main__':
    # Failed children must not leave large core dumps in a source checkout.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    unittest.main(verbosity=2)
