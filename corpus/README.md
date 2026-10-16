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

## Findings (tested 2026-10-16)

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

A fresh blank-form render check on 2026-10-16, after the image, table, scripting,
formatting, pagination and dialog changes, rendered all 129 forms without a failed
render. 119 forms logged no script errors. The remaining 10 logged 26 error
occurrences, including repeated calculation passes.

| Department | Kind | Forms rendered | No script errors | Script error occurrences |
|---|---|---|---|---|
| Global Affairs Canada | Dynamic | 1 | 1 | 0 |
| IRCC | Dynamic | 14 | 14 | 0 |
| CRA | Dynamic | 90 | 81 | 20 |
| CRA | Static | 6 | 6 | 0 |
| Service Canada | Static | 10 | 10 | 0 |
| IRCC | Static | 4 | 4 | 0 |
| IRCC (passports) | Static | 4 | 3 | 6 |

These are rendering and script-execution checks on blank forms. Only the consent
letter has been verified end to end by filling, generating, printing, saving and
reopening it. No script errors does not establish that a form's calculations,
validation, data binding or barcodes produce correct submission-ready output.
The patched viewer continues to use ordinary PDF pages for static XFA forms;
this check explicitly renders those forms through the engine too.

The previous results described PNG images, table layout, FormCalc and barcodes as
unimplemented. Those features now have implementations and synthetic tests. The
current render logs report no unsupported images in the 105 dynamic forms.
Five static forms still log image decoding failures: TIFF in the four passport
forms and JPEG in ISP-1300. Feature coverage and correctness still need tests
with filled forms.

Forms still reporting script errors:

| File | Pages | Error occurrences |
|---|---|---|
| `inns3-fill-19e.pdf` | 1 | 2 |
| `rc243-fill-26e.pdf` | 5 | 6 |
| `t1000-3-fill-21e.pdf` | 2 | 1 |
| `t1235-fill-20e.pdf` | 2 | 1 |
| `t1236-fill-19e.pdf` | 2 | 3 |
| `t1441-fill-24e.pdf` | 3 | 1 |
| `t3ao-fill-23e.pdf` | 1 | 2 |
| `t3inns3-fill-23e.pdf` | 1 | 2 |
| `t7dr-fill-19e.pdf` | 1 | 2 |
| `pptc040.pdf` | 10 | 6 |

The logs identify several follow-up areas: Acrobat document APIs used by
accessibility helpers (`dynamicXFAForm`, `getField` and field `userName`), default
caption/value nodes used by paper-barcode scripts, and unresolved form-node
references in the TFSA return, T1000-3 and a passport form. Investigate these
against the source templates and synthetic reproductions before changing lookup
rules or claiming the affected forms work.

Broader implementation gaps include explicit `dataRef` bindings and synchronization
with the data DOM, some FormCalc functions and predicates, time picture clauses,
embedded fonts and linked/SVG images. During interactive editing Evince now asks
script questions and accepts prompt text; scripts run before a view is attached,
and command-line rendering, retain the engine's automatic fallback answers.

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
