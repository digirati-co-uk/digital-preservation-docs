#!/bin/bash
npm install mmdc
sed -E "s/^([^]]+)(\[[^]]*\])\(([^)]*)\)/\1\2({{ site.baseurl }}{% link pages\/sequence-diagrams\/\3 %})/" sequence-diagrams/README.md > index.md
for f in sequence-diagrams/*.md; do mmdc -i $f --outputFormat=png --scale=2 -o pages/$f; done
rm pages/sequence-diagrams/README.md