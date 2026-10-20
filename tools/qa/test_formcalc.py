#!/usr/bin/env python3
"""FormCalc built-in functions against the examples of Adobe's FormCalc reference.

PDFXFA=/path/to/pdfxfa python3 tools/qa/test_formcalc.py
Each case is a field whose FormCalc calculate script shows "Rn=<result>".
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_core import pdf  # noqa: E402

# (expression, expected, time zone). Numbers match to 1e-9 relative unless a
# tolerance is given as a fourth item.
CASES = [
    ('Apr(35000, 269.50, 360)', 0.08515404566, None, 1e-5),  # Adobe's own iteration is coarse
    ('Apr(210000 * 0.75, 850 + 110, 25 * 26)', 0.07161332404, None, 1e-5),
    ('CTerm(0.02, 1000, 100)', 116.2767474515, None),
    ('CTerm(0.10, 500000, 12000)', 39.13224648502, None),
    ('FV(400, 0.10 / 12, 30 * 12)', 904195.16991842445, None),
    ('FV(1000, 0.075 / 4, 10 * 4)', 58791.96145535981, None),
    ('IPmt(30000, 0.085, 295.50, 7, 3)', 624.8839283142, None),
    ('IPmt(160000, 0.0475, 980, 24, 12)', 7103.80833569485, None),
    ('IPmt(15000, 0.065, 65.50, 15, 1)', 0, None),
    ('NPV(0.065, 5000)', 4694.83568075117, None),
    ('NPV(0.10, 500, 1500, 4000, 10000)', 11529.60863329007, None),
    ('NPV(0.0275 / 12, 50, 60, 40, 100, 25)', 273.14193838457, None),
    ('Pmt(150000, 0.0475 / 12, 25 * 12)', 855.17604207164, None),
    ('Pmt(25000, 0.085, 12)', 3403.82145169876, None),
    ('PPmt(30000, 0.085, 295.50, 7, 3)', 261.6160716858, None),
    ('PPmt(160000, 0.0475, 980, 24, 12)', 4656.19166430515, None),
    ('PV(400, 0.10 / 12, 30 * 12)', 45580.32799074439, None),
    ('Rate(12000, 8000, 5)', 0.0844717712, None),
    ('Rate(10000, 0.25 * 5000, 4 * 12)', 0.04427378243, None),
    ('Term(475, .05, 1500)', 3.00477517728, None),
    ('Term(2500, 0.0275 + 0.0025, 5000)', 1.97128786369, None),
    ('WordNum(123.45)', 'One Hundred and Twenty-three', None),
    ('WordNum(1154.67, 2)', 'One Thousand One Hundred Fifty-four Dollars And Sixty-seven Cents', None),
    ('WordNum(43, 2)', 'Forty-three Dollars And Zero Cents', None),
    ('WordNum(-1)', '*', None),
    ('UnitValue("2in")', 2, None),
    ('UnitValue("2in", "cm")', 5.08, None),
    ('UnitValue("6", "pt")', 432, None),
    ('UnitValue("A", "cm")', 0, None),
    ('UnitValue("5.08cm", "kilograms")', 2, None),
    ('UnitType("36 in")', 'in', None),
    ('UnitType("2.54centimeters")', 'cm', None),
    ('UnitType("picas")', 'pc', None),
    ('UnitType("2.cm")', 'cm', None),
    ('UnitType("2.zero cm")', 'in', None),
    ('UnitType("kilometers")', 'in', None),
    ('Encode("""hello, world!""", "url")', '%22hello,%20world!%22', None),
    ('Encode("ÁÂÃÄÅÆ", "html")', '&#xc1;&#xc2;&#xc3;&#xc4;&#xc5;&#xc6;', None),
    ('Decode("&AElig;&Aacute;&Acirc;&Aacute;&Acirc;", "html")', 'ÆÁÂÁÂ', None),
    ('Decode("&lt;a&gt;&amp;&apos;", "xml")', "<a>&'", None),
    ('Format("MMM D, YYYY", "20020901")', 'Sep 1, 2002', None),
    ('Format("$9,999,999.99", 1234567.89)', '$1,234,567.89', None),
    ('Parse("MMM D, YYYY", "Sep 1, 2002")', '2002-09-01', None),
    ('Parse("$9,999,999.99", "$1,234,567.89")', 1234567.89, None),
    ('Date2Num("Mar 15, 1996")', 35138, None),
    ('Date2Num("1/1/1900", "D/M/YYYY")', 1, None),
    ('Date2Num("03/15/96", "MM/DD/YY")', 35138, None),
    ('Date2Num("96-08-20", "YY-MM-DD", "fr_FR")', 35296, None),
    ('Date2Num("1/3/00", "D/M/YY") - Date2Num("1/2/00", "D/M/YY")', 29, None),
    ('Num2Date(1, "DD/MM/YYYY")', '01/01/1900', None),
    ('Num2Date(Date2Num("Mar 15, 2000") - Date2Num("98-03-15", "YY-MM-DD", "fr_CA"))', 'Jan 1, 1902', None),
    ('DateFmt(1)', 'M/D/YY', None),
    ('DateFmt(2, "fr_CA")', 'YY-MM-DD', None),
    ('LocalDateFmt(2, "fr_CA")', 'aa-MM-jj', None),
    ('TimeFmt(1)', 'h:MM A', None),
    ('TimeFmt(2, "fr_CA")', 'HH:MM:SS', None),
    ('LocalTimeFmt(2, "fr_CA")', 'HH:mm:ss', None),
    ('Time2Num("00:00:00 GMT", "HH:MM:SS Z")', 1, None),
    ('Time2Num("13:13:13 GMT", "HH:MM:SS Z", "fr_FR")', 47593001, None),
    ('Time2Num("1:13:13 PM")', 76393001, 'PST8'),
    ('(Time2Num("13:13:13", "HH:MM:SS") - Time2Num("13:13:13 GMT", "HH:MM:SS Z")) / (60 * 60 * 1000)', 5, 'EST5'),
    ('Num2GMTime(1, "HH:MM:SS")', '00:00:00', None),
    ('Num2GMTime(65593001, "HH:MM:SS Z")', '18:13:13 GMT', None),
    ('Num2Time(65593001, "HH:MM:SS Z")', '13:13:13 EST', 'EST5'),
    ('Num2Time(1, "HH:MM:SS")', '09:00:00', 'JST-9'),
    ('IsoTime2Num("00:00:00Z")', 1, None),
    ('IsoTime2Num("13:13:13")', 76393001, 'PST8'),
    ('IsoTime2Num("13")', 64800001, 'EST5'),
    ('Eval("10*3+5*4")', 50, None),
    ('Concat("x", Null(), "y")', 'xy', None),
    ('Ref("hello")', 'hello', None),
]


def template(cases):
    fields = ''.join(
        f'<field name="f{i}" w="7.5in" h="0.25in"><ui><textEdit/></ui><calculate><script>'
        f'Concat("R{i}=", {escape(c[0])})</script></calculate></field>' for i, c in enumerate(cases))
    return ('<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">'
            '<template xmlns="http://www.xfa.org/schema/xfa-template/3.3/">'
            '<subform name="form1" layout="tb" locale="en_US">'
            '<pageSet><pageArea name="Page1"><contentArea x="0.5in" y="0.5in" w="7.5in" h="10in"/>'
            '<medium short="8.5in" long="11in"/></pageArea></pageSet>'
            + fields + '</subform></template></xdp:xdp>')


class FormCalcTests(unittest.TestCase):
    def results(self, cases, tz):
        binary = str(Path(os.environ.get('PDFXFA', '_install/bin/pdfxfa')).resolve())
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp, 'in.pdf'), Path(tmp, 'out.pdf')
            src.write_bytes(pdf(template(cases)))
            env = dict(os.environ, TZ=tz or 'UTC')
            run = subprocess.run([binary, '-log', str(src), str(out)], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr.decode(errors='replace')[-2000:])
            text = subprocess.check_output(['pdftotext', str(out), '-']).decode()
            return dict(re.findall(r'R(\d+)=(.*)', text)), run.stderr.decode(errors='replace')

    def test_functions(self):
        for tz in sorted({c[2] for c in CASES}, key=str):
            cases = [c for c in CASES if c[2] == tz]
            got, log = self.results(cases, tz)
            for i, case in enumerate(cases):
                expr, want = case[0], case[1]
                with self.subTest(expr=expr, tz=tz):
                    self.assertIn(str(i), got, f'no result; log:\n{log[-1500:]}')
                    value = got[str(i)].strip()
                    if isinstance(want, str):
                        self.assertEqual(value, want)
                    else:
                        tol = case[3] if len(case) > 3 else 1e-9
                        self.assertAlmostEqual(float(value), want, delta=max(abs(want) * tol, 1e-9))


if __name__ == '__main__':
    unittest.main(verbosity=1)
