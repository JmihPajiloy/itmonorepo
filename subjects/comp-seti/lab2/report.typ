#import "@preview/modern-g7-32:0.2.0": gost
#import "/templates/title-page.typ": title-page

#show: gost.with(hide-title: true)
//#set text(font: "Times New Roman")
//#set par(spacing: 0.7em)
//#show raw: set text(font: "Courier New", size: 14pt)
//#set table(inset: 0pt, column-gutter: 0.7em, row-gutter: 0.5em, stroke: none)
//#show table: set par(justify: false, first-line-indent: 0pt, leading: 0.35em, spacing: 0pt)
//#show figure.where(kind: table): it => block(breakable: false, it)
//#show figure: set par(first-line-indent: 0pt)

#title-page(
  "Компьютерные сети",
  "2",
  "Анализ трафика компьютерных сетей утилитой Wireshark",
  "Шибаев Иван Дмитриевич",
  "Есипов Дмитрий Андреевич",
  group: "N3352",
  footer: align(center)[Санкт-Петербург\ 2026],
)

#outline(depth: 2)

#include "report-core.typ"
#include "report-media.typ"

#bibliography("references.bib")
