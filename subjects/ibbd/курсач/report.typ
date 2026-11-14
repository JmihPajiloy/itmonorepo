#import "@preview/modern-g7-32:0.2.0": gost, appendixes
#import "details.typ": authors, topic
#import "forms.typ": title-page, assignment-page, schedule-page, abstract-page

#set document(title: [#topic], author: authors.map(author => author.text))
#show: gost.with(hide-title: true, margin: (left: 30mm, right: 10mm, top: 20mm, bottom: 20mm))
#set text(font: "Times New Roman")
#show raw: set text(font: "Courier New", size: 10pt)
#show table: set text(size: 12pt)
#show table.cell: set par(justify: false, first-line-indent: 0pt, leading: .45em)
#show figure.caption: set par(first-line-indent: 0pt, leading: .45em)
#show figure.where(kind: raw): set block(breakable: true)
#show figure.where(kind: table): it => block(breakable: false, it)
#show outline.entry: set par(first-line-indent: 0pt, leading: .45em, spacing: .6em)
#show outline.entry: set block(above: .6em, below: .6em)
#set outline(depth: 2)
#set ref(supplement: auto)

#title-page
#assignment-page
#schedule-page
#abstract-page
#[
  #show "Введение": upper
  #show "Заключение": upper
  #show "Список использованных источников": upper
  #outline()
]
#show heading.where(body: [СПИСОК СОКРАЩЕНИЙ И УСЛОВНЫХ ОБОЗНАЧЕНИЙ]): it => align(center, it)
#heading(numbering: none)[СПИСОК СОКРАЩЕНИЙ И УСЛОВНЫХ ОБОЗНАЧЕНИЙ]
#[
  #set par(first-line-indent: 0pt, justify: false, spacing: .6em)
  БД — база данных #linebreak()
  ИС — информационная система #linebreak()
  СУБД — система управления базами данных #linebreak()
  CSRF — подделка межсайтового запроса #linebreak()
  ER — модель «сущность — связь» #linebreak()
  PITR — восстановление на заданный момент #linebreak()
  RLS — политики безопасности на уровне строк #linebreak()
  SCRAM — механизм парольной аутентификации с обменом доказательствами #linebreak()
  TLS — протокол защиты транспортного соединения #linebreak()
  WAL — журнал предзаписи PostgreSQL #linebreak()
  XSS — внедрение сценария в веб-страницу
]

#include "chapters/introduction.typ"
#include "chapters/database.typ"
#include "chapters/service.typ"
#include "chapters/security.typ"
#include "chapters/recovery.typ"
#include "chapters/conclusion.typ"
#bibliography("references.bib")

#show: appendixes
#include "chapters/appendices.typ"
