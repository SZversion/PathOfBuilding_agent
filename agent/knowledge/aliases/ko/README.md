# Korean PoE1 item aliases

`items-3.29.json` is generated from the translated PoB CSV files listed in its
`sources` metadata. Values are copied exactly; the importer does not trim or
normalize whitespace, punctuation, or spelling.

The generated flask-name CSV contains combinatorial prefix/base/suffix names.
It is preserved exactly in `flask-names-3.29.csv.gz` rather than duplicated into
the canonical JSON alias index; those names can be indexed from the compressed
source when flask search is implemented.
