# Government of Canada forms corpus

Real public forms used to measure what free PDF software can and can't do with XFA.
`forms.tsv` lists each form's official page, download URL, the SHA-256 of the version
tested, whether it is dynamic or static XFA, and the XFA features it uses. The forms
belong to the Government of Canada and are not redistributed here: download them
with `scripts/fetch-corpus.sh`.

```sh
scripts/fetch-corpus.sh   # download into corpus/files/ and check the tested versions
scripts/check-corpus.sh   # page 1 without XFA support vs. the XFA engine, per form
```

## Two kinds of XFA form

- **Dynamic XFA** (`NeedsRendering`): the PDF has no real pages, only a fallback page
  saying "Please wait… If this message is not eventually replaced by the proper
  contents of the document, your PDF viewer may not be able to display this type of
  document", or "requires Adobe Reader 8 or higher". The form exists only as XFA, which
  the viewer must lay out and script itself. Poppler (Evince, Okular, Papers, most Linux
  viewers) doesn't, so these forms can't be used at all.
- **Static XFA**: the PDF also carries ordinary pages and AcroForm fields, so other
  viewers can show and fill it. The form's scripts don't run there: for example
  calculations, sections that appear as you answer, validation, and the barcodes that
  some forms print.

## Findings (tested 2026-10-16, engine rechecked 2026-10-19)

This project started with Global Affairs Canada's
[consent letter for children travelling outside Canada](https://travel.gc.ca/travelling/children/consent-letter)
(`consent-letter-2123.pdf`): the letter parents sign when a child travels abroad
without one or both of them. Linux viewers show only "requires Adobe Reader 8 or higher". With this
repository's patches it works end to end: fill in, generate the letter, print, and
save and reopen.

Without XFA support, all 105 dynamic forms in the corpus show only the fallback page:

| Department | Dynamic: unusable on Linux | Static: fillable, scripts don't run | Coverage |
|---|---|---|---|
| Global Affairs Canada | 1 | 0 | the consent letter |
| IRCC (immigration) | 14 | 4 | 18 commonly used forms |
| IRCC (passports) | 0 | 4 | the 4 passport applications |
| CRA | 90 | 6 | **all 1,168 fillable forms** in CRA's catalogue were checked; the 90 dynamic ones and 6 static examples are listed |
| ESDC (Service Canada) | 0 | 10 | 10 commonly used forms |

IRCC's help centre states that its forms
[need Adobe Reader 10 or higher](https://ircc.canada.ca/english/helpcentre/answer.asp?qnum=140&top=18)
and that the Validate button's barcodes
[don't work in other software](https://ircc.canada.ca/english/helpcentre/answer.asp?qnum=767&top=18).
Adobe has not released Acrobat Reader for Linux since version 9.

The 90 CRA forms are 8% of its fillable forms. Among them are forms that many people
and organizations must file:

- T1135 Foreign Income Verification Statement
- RC243 Tax-Free Savings Account (TFSA) Return
- RC728 First Home Savings Account (FHSA) Return
- T657 Calculation of Capital Gains Deduction
- T3010 Registered Charity Information Return
- T3SCH15 Beneficial Ownership Information of a Trust

Other dynamic CRA forms are foreign-reporting returns (T106, T1134, T1141, T1142), SR&ED
claims (T661, T1322), payment vouchers, and 58 CPT forms for CPP/EI ruling requests.

The IRCC and ESDC rows are hand-picked samples of commonly used forms, so their
proportions are an illustration. The CRA row covers its whole catalogue as of the test
date.

### The XFA engine in this repository

A blank-form render check on 2026-10-19 rendered all 129 forms without a failed
render. 125 forms logged no script errors. The remaining 4 logged 15 error
occurrences, counting repeated calculation passes, and each of them comes from a
mistake in the form itself (below), which Acrobat would report too. No form reports
an unsupported image.

| Department | Kind | Forms rendered | No script errors | Script error occurrences |
|---|---|---|---|---|
| Global Affairs Canada | Dynamic | 1 | 1 | 0 |
| IRCC | Dynamic | 14 | 14 | 0 |
| CRA | Dynamic | 90 | 87 | 9 |
| CRA | Static | 6 | 6 | 0 |
| Service Canada | Static | 10 | 10 | 0 |
| IRCC | Static | 4 | 4 | 0 |
| IRCC (passports) | Static | 4 | 3 | 6 |

These are rendering and script-execution checks on blank forms. Only the consent
letter has been verified end to end by filling, generating, printing, saving and
reopening it, including switching its language back and forth with every section
filled in. The later editing audit (`TESTING.md` in the public source export)
additionally exercises 430 text
and choice edits across all 129 forms, saving and reopening them under sanitizers,
and documents the INNS3 template's year recalculation on reopening. No script
errors does not establish that a form's calculations,
validation, data binding or barcodes produce correct submission-ready output.
The patched viewer continues to use ordinary PDF pages for static XFA forms;
this check explicitly renders those forms through the engine too.

Forms still reporting script errors, all because of the form:

| File | Error occurrences | Cause |
|---|---|---|
| `rc243-fill-26e.pdf` | 6 | Calculations read `details.totals.numTotal`; the table has no `details` subform (`totals` is its child). |
| `t1000-3-fill-21e.pdf` | 1 | `docReady` reads `form1.Page1.Person9_sub`; `Person9_sub` is a sibling of `Page1`, not its child. |
| `t1236-fill-19e.pdf` | 2 | A `ready` script sets `SectionA_A1_Charity_BN.h`; no object has that name (the field is `Charity_BN`). |
| `pptc040.pdf` | 6 | Barcode fields read `CurrentAddress.Prov` and `MailingAddress.Prov`; `Prov` remains only in the `…-Old-With-Prov` copies of those subforms. |

The 483 errors earlier logs showed for four CRA forms came from `event.target`, which
in Acrobat is the Doc object; CRA's accessibility helpers test its `dynamicXFAForm`.
Four CRA paper-forms barcodes (T7DR, INNS3, T3AO, T3INNS3) now encode their content
through data nodes and manifests. The images earlier logs called unsupported are
links to files on the form author's computer (`..\..\..\Graphics\...`); embedded
images all decode.

Remaining gaps, described in `KNOWN_ISSUES.md`: `dataRef` bindings with predicates,
the form's own typefaces (text uses the standard fonts and, for other characters,
similar system fonts), SVG images, and automatic answers to script questions when
no viewer is attached.

`results.tsv` contains the current per-form results for all 129 forms, produced by
`scripts/check-corpus.sh`. The downloaded files are checked against `forms.tsv`.

## Upstream reports about XFA

- Poppler [#530](https://gitlab.freedesktop.org/poppler/poppler/-/issues/530), "Poppler
  doesn't render PDFs that check Adobe Reader is there using JavaScript": open since
  January 2008 (originally freedesktop bug 14265).
- Poppler [#1154](https://gitlab.freedesktop.org/poppler/poppler/-/issues/1154), "Can we
  consider using code from PDFium or pdf.js to have xfa support?": opened 2021, closed.
- Okular [KDE bug 263042](https://bugs.kde.org/show_bug.cgi?id=263042), "XFA Forms are
  not supported": opened January 2011, reopened.
