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

The engine lays out all 105 dynamic forms, each in under a quarter of a second. How far
each one works:

| Department | Works | Lays out | Partly | No |
|---|---|---|---|---|
| Global Affairs Canada | 1 | 0 | 0 | 0 |
| IRCC | 0 | 0 | 6 | 8 |
| CRA | 0 | 66 | 20 | 4 |

- **Works**: verified end to end, by filling in, generating, printing, saving and
  reopening. So far only the consent letter.
- **Lays out**: the blank form lays out and its scripts run without errors, but it has
  not been tested by filling it in. All CRA forms are missing their PNG images
  (the agency logo).
- **Partly**: lays out, but some scripts fail, or tables are stacked instead of laid out
  in columns.
- **No**: the form's essential function needs a barcode, which the engine doesn't draw
  yet. On the IRCC applications this is the **Validate** button, which checks the
  answers and encodes them into 2D barcodes; IRCC's help centre says it works only in
  Adobe Reader. The four CRA payment vouchers also carry a barcode.

The IRCC forms and the consent letter:

| Form | Pages | Script errors | Result | Missing in the engine |
|---|---|---|---|---|
| Recommended consent letter for children travelling abroad (2123) | 2 | 0 | Works | - |
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

Selected CRA forms:

| Form | Pages | Script errors | Result | Missing in the engine |
|---|---|---|---|---|
| T1135 Foreign Income Verification Statement | 8 | 1 | Partly | table layout, images: png |
| RC243 Tax-Free Savings Account (TFSA) Return | 5 | 9 | Partly | table layout, images: png |
| RC728 2025 First Home Savings Account (FHSA) Return | 5 | 3 | Partly | table layout, images: png |
| T3010 Registered Charity Information Return | 13 | 0 | Partly | table layout, images: png |
| T657 Calculation of Capital Gains Deduction | 7 | 0 | Partly | table layout, images: png |
| T3SCH15 Beneficial Ownership Information of a Trust | 2 | 0 | Lays out | images: png |
| T1134 Information Return Relating to Controlled and Non-Controlled Foreign Affiliates (2021 and later taxation years) | 44 | 0 | Partly | table layout, images: png |
| T106 Information Return of Non-Arm's Length Transactions with Non-Residents (2025 and later tax years) T106 Summary Form | 9 | 1 | Partly | images: png |
| T1141 Information Return in Respect of Contributions to Non-Resident Trusts, Arrangements, or Entities (2025 and later tax years) | 9 | 1 | Partly | table layout, images: png |
| T1142 Information Return in Respect of Distributions from and Indebtedness to a Non-Resident Trust | 7 | 0 | Partly | table layout, images: png |
| T661 Scientific Research and Experimental Development (SR&ED) Expenditures Claim | 12 | 0 | Partly | table layout, images: png |
| T2SCH75 Clean Technology Investment Tax Credit | 4 | 0 | Partly | table layout, images: png |
| RC4649 Country-by-Country Report | 12 | 1 | Partly | table layout, images: png |
| NR302 Declaration of eligibility for benefits (reduced tax) under a tax treaty for a partnership with non-resident partners | 28 | 12 | Partly | FormCalc, table layout, images: png |

`results.tsv` has the per-form results for all 129 forms, as produced by
`scripts/check-corpus.sh` on the test date.

The engine also renders all 24 static forms: the 16 CRA and Service Canada forms with
no script errors, the IRCC and passport ones with 4 to 12. The patched Evince only uses
the engine for dynamic forms, so static ones open as they did before.

## Upstream reports about XFA

- Poppler [#530](https://gitlab.freedesktop.org/poppler/poppler/-/issues/530), "Poppler
  doesn't render PDFs that check Adobe Reader is there using JavaScript": open since
  January 2008 (originally freedesktop bug 14265).
- Poppler [#1154](https://gitlab.freedesktop.org/poppler/poppler/-/issues/1154), "Can we
  consider using code from PDFium or pdf.js to have xfa support?": opened 2021, closed.
- Okular [KDE bug 263042](https://bugs.kde.org/show_bug.cgi?id=263042), "XFA Forms are
  not supported": opened January 2011, reopened.
