#!/usr/bin/env python3
"""Dump the XFA packets of a PDF into a directory, one XML file per packet.

Usage: python3 -I tools/xfa_dump.py <file.pdf> <outdir>
Needs pikepdf (pip install pikepdf). Handles owner-password-only encryption.
"""
import os
import sys

import pikepdf


def main(pdf_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    pdf = pikepdf.open(pdf_path)
    acroform = pdf.Root.get("/AcroForm")
    if acroform is None or "/XFA" not in acroform:
        sys.exit("no XFA in this PDF")
    xfa = acroform.XFA

    # XFA is either one stream with the whole XDP, or an array of name/stream pairs.
    if isinstance(xfa, pikepdf.Stream):
        packets = [("xdp", xfa.read_bytes())]
    else:
        packets = [(str(xfa[i]), xfa[i + 1].read_bytes()) for i in range(0, len(xfa), 2)]

    for n, (name, data) in enumerate(packets):
        path = os.path.join(outdir, f"{n:02d}_{name}.xml")
        with open(path, "wb") as f:
            f.write(data)
        print(f"{name:12} {len(data):8} bytes  {path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
