#let title-page(
  discipline,
  number,
  title,
  student,
  instructor,
  group: "N3352",
  coauthors: (),
  city: none,
  year: none,
) = page(footer: none)[
  #align(center)[
    #set text(12pt)
    #set par(justify: false)
    *Министерство науки и высшего образования Российской Федерации*\
    ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ АВТОНОМНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ ВЫСШЕГО ОБРАЗОВАНИЯ\
    *НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ ИТМО*
    #v(4em)
    *Факультет безопасности информационных технологий*\
    #v(1em)
    *Дисциплина:*\
    «#discipline»
    #v(2em)
    *ОТЧЁТ ПО ЛАБОРАТОРНОЙ РАБОТЕ №#number*\
    «#title»
  ]
  #v(8em)
  #align(right)[
    #box(width: 240pt)[
      #set align(right)
      #set text(size: 11pt)

      #if coauthors.len() > 0 [*Выполнили:*] else [*Выполнил:*] \
      #student, студент группы #group
      #v(0.6em)
      #line(length: 50%, stroke: 1pt)
      #align(center)[#move(dx: 25%, dy: -14pt)[#text(size: 8pt)[(подпись)]]]

      #for coauthor in coauthors [
        #v(1.2em)
        \
        #coauthor, студент группы #group
        #v(0.6em)
        #line(length: 50%, stroke: 1pt)
        #align(center)[#move(dx: 25%, dy: -14pt)[#text(size: 8pt)[(подпись)]]]
      ]

      #if instructor != none [
        #v(1.5em)

        *Проверил:* \
        #instructor
        #v(0.6em)
        #line(length: 50%, stroke: 1pt)
        #align(center)[#move(dx: 25%, dy: -14pt)[#text(size: 8pt)[(подпись)]]]
      ]
    ]
  ]
  #if city != none and year != none [
    #place(bottom + center, dy: -1em)[
      #align(center)[#city — #year]
    ]
  ]
]
