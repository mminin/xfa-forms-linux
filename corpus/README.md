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

All 15 dynamic forms show only the fallback page without XFA support. They are most of
the IRCC immigration applications sampled, and the Global Affairs Canada consent letter
for children travelling abroad. IRCC's help centre states that its forms
[need Adobe Reader 10 or higher](https://ircc.canada.ca/english/helpcentre/answer.asp?qnum=140&top=18)
and that the Validate button's barcodes
[don't work in other software](https://ircc.canada.ca/english/helpcentre/answer.asp?qnum=767&top=18).
Adobe has not released Acrobat Reader for Linux since version 9.

All 24 static forms sampled show their content without XFA support. They are all the CRA
and Service Canada (ESDC) forms sampled, the passport applications and four IRCC forms.

| Department | Dynamic (unusable without XFA) | Static (fillable, scripts don't run) |
|---|---|---|
| IRCC (immigration) | 14 of 18 | 4 |
| IRCC (passports) | 0 of 4 | 4 |
| Global Affairs Canada | 1 of 1 | 0 |
| CRA | 0 of 6 | 6 |
| ESDC (Service Canada) | 0 of 10 | 10 |

The sample is small and was chosen by hand from commonly used forms, so the proportions
are an illustration, not a census.

### The XFA engine in this repository

| Form | Pages | Script errors | Usable? | Missing in the engine |
|---|---|---|---|---|
| Recommended consent letter for children travelling abroad (2123) | 2 | 0 | Yes | - |
| Generic Application Form for Canada (IMM 0008) | 6 | 10 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Application for a Study Permit Made Outside of Canada (IMM 1294) | 6 | 17 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Application for a Work Permit Made Outside of Canada (IMM 1295) | 6 | 16 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Application to Sponsor, Sponsorship Agreement and Undertaking (IMM 1344) | 10 | 40 | No | barcodes (Validate), FormCalc, images: bmp, tif |
| Application for visitor visa (temporary resident visa) (IMM 5257) | 6 | 15 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Additional Family Information (IMM 5406) | 5 | 6 | Partly | table layout |
| Application for a Permanent Resident Card (PR card) or Permanent Resident Travel Document (PRTD) [IMM 5444] | 8 | 16 | Partly | FormCalc, table layout |
| Relationship Information And Sponsorship Evaluation Form (IMM 5532) | 20 | 2 | Partly | table layout |
| Supplementary Information: Your Travels (IMM 5562) | 3 | 10 | Partly | - |
| Schedule A: Background / Declaration Form (IMM 5669) | 12 | 24 | Partly | table layout |
| Family Information Form – Visitors, Students and Workers (IMM 5707) | 4 | 3 | Partly | - |
| Application to Change Conditions, Extend my Stay or Remain in Canada as a Visitor or Temporary Resident Permit Holder (IMM 5708) | 7 | 20 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Application to Change Conditions, Extend my Stay or Remain in Canada as a Student (IMM 5709) | 7 | 21 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |
| Application to Change Conditions, Extend my Stay or Remain in Canada as a Worker (IMM 5710) | 6 | 21 | No | barcodes (Validate), FormCalc, table layout, images: bmp, tif |

What "usable" means here:

- **Yes**: the form lays out completely, and its scripts run without errors.
- **Partly**: the form lays out and can be filled, but some scripts fail, tables are
  stacked instead of laid out in columns, or some images are missing.
- **No**: the form's essential function doesn't work. For these IRCC applications that
  is the **Validate** button, which checks the answers and encodes them into 2D barcodes
  on the form. IRCC's help centre says it works only in Adobe Reader. This engine doesn't draw barcodes or run FormCalc yet.

The engine also renders all 24 static forms: the 16 CRA and Service Canada forms with
no script errors, the IRCC and passport ones with 4 to 12. The patched Evince only uses
the engine for dynamic forms, so static ones open as they did before.

The full consent-letter workflow (fill in, generate the letter, print, save and reopen) is
the only one verified end to end. Every other result here is from automated rendering
of the blank form, not from filling it in.

## Upstream reports about XFA

- Poppler [#530](https://gitlab.freedesktop.org/poppler/poppler/-/issues/530), "Poppler
  doesn't render PDFs that check Adobe Reader is there using JavaScript": open since
  January 2008 (originally freedesktop bug 14265).
- Poppler [#1154](https://gitlab.freedesktop.org/poppler/poppler/-/issues/1154), "Can we
  consider using code from PDFium or pdf.js to have xfa support?": opened 2021, closed.
- Okular [KDE bug 263042](https://bugs.kde.org/show_bug.cgi?id=263042), "XFA Forms are
  not supported": opened January 2011, reopened.
