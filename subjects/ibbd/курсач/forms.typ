#import "details.typ": *

#let university = align(center)[
  #set par(first-line-indent: 0pt, justify: false, leading: .35em)
  #text(10pt)[МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ] #linebreak()
  #text(9pt, weight: "bold")[ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ АВТОНОМНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ ВЫСШЕГО ОБРАЗОВАНИЯ] #linebreak()
  *«НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ ИТМО»*
]

#let form-heading(title) = [
  #university
  #v(8mm)
  #align(center, strong(title))
  #v(5mm)
]

#let rule = line(length: 100%, stroke: .5pt)
#let fit-line(content) = block(width: 100%, inset: (bottom: 2pt), stroke: (bottom: .5pt))[#content]
#let fields = grid(
  columns: (43mm, 1fr), row-gutter: 2mm, column-gutter: 3mm,
  [Студенты], fit-line(short-authors),
  [Факультет], fit-line(faculty),
  [Группа], fit-line(group),
  [Направление], fit-line(direction),
  [Руководитель], fit-line(supervisor),
  [Дисциплина], fit-line(discipline),
  [Наименование темы], fit-line(topic),
)

#let signatures = grid(
  columns: (45mm, 1fr), row-gutter: 3mm, column-gutter: 3mm,
  [Руководитель], [#rule #align(center, text(10pt)[Подпись, дата])],
  [Шибаев И. Д.], [#rule #align(center, text(10pt)[Подпись, дата])],
  [Малышев Г. И.], [#rule #align(center, text(10pt)[Подпись, дата])],
)

#let form(body) = page(footer: none)[
  #set text(font: "Times New Roman", size: 12pt)
  #set par(justify: false, first-line-indent: 0pt, spacing: .7em, leading: .55em)
  #set align(left)
  #body
]

#let title-signature(name) = grid(
  columns: (1fr, auto, 24mm),
  column-gutter: 1.5mm,
  row-gutter: 1.5mm,
  align: (center, center, center),
  fit-line(name),
  [/],
  fit-line(hide([А])),
  text(9pt, style: "italic")[ФИО],
  [],
  text(9pt, style: "italic")[Подпись],
)

#let title-page = form[
  #university
  #v(14mm)
  #align(center, strong(faculty))
  #v(6mm)
  Направление подготовки: #direction #linebreak()
  Образовательная программа: #program

  #v(13mm)
  #align(center)[
    Дисциплина #linebreak()
    «#discipline»
    #v(9mm)
    #text(size: 15pt, weight: "bold")[КУРСОВАЯ РАБОТА] #linebreak()
    на тему «#topic»
  ]
  #v(13mm)
  #align(right, block(width: 92mm)[
    *Выполнили студенты:* #linebreak()
    группа/поток #group

    #for author in authors {
      title-signature(author)
      v(2mm)
    }
    #v(8mm)
    *Проверила:*

    #title-signature(examiner)
    #v(6mm)
    #line(length: 47mm, stroke: .5pt)
    #text(9pt, style: "italic")[
      Отметка о выполнении (отлично, хорошо, удовлетворительно)
    ]
    #v(4mm)
    #line(length: 28mm, stroke: .5pt)
    #box(width: 28mm)[#align(center, text(9pt, style: "italic")[Дата])]
  ])
  #v(1fr)
  #align(center)[Санкт-Петербург #linebreak() #year г.]
]

#let assignment-page = form[
  #form-heading[ЗАДАНИЕ НА КУРСОВУЮ РАБОТУ]
  #fields
  #v(7mm)
  *Задание.* Спроектировать базу данных мастерской, реализовать её в PostgreSQL и разработать веб-сервис для приёмщика, реставратора и администратора. Настроить разграничение доступа, журналирование и шифрование секретов. Проверить работу механизмов защиты и восстановление данных.

  *Краткие методические указания.* Построить модель «сущность — связь», обосновать третью нормальную форму, реализовать защиту средствами СУБД и приложения. Для оценки использовать сценарии разрешённых и запрещённых операций и сверку состояния до изменений и после восстановления.

  *Содержание пояснительной записки.* Введение. Моделирование и реализация базы данных. Архитектура и функции веб-сервиса. Аудит безопасности. Резервирование и восстановление. Заключение и список использованных источников.

  *Рекомендуемая литература.* Методические указания по ИББД. Документация PostgreSQL 14 по политикам строк, аутентификации, криптографическим функциям и восстановлению из архива. Документация Flask и Psycopg.

  #v(1fr)
  #signatures
]

#let schedule-page = form[
  #form-heading[ГРАФИК ВЫПОЛНЕНИЯ КУРСОВОЙ РАБОТЫ]
  #fields
  #v(8mm)
  #table(
    columns: (8mm, 1.45fr, .68fr, .68fr, 1fr),
    inset: (x: 4pt, y: 6pt), align: (center, left, center, center, center),
    table.header(
      table.cell(rowspan: 2)[№],
      table.cell(rowspan: 2)[Наименование этапа],
      table.cell(colspan: 2, align: center)[Дата завершения],
      table.cell(rowspan: 2)[Оценка и подпись руководителя],
      [Планируемая], [Фактическая],
    ),
    [1], [Модель и реализация базы данных], [], [], [],
    [2], [Защита базы данных и разработка веб-сервиса], [], [], [],
    [3], [Проверка защиты и восстановления данных], [], [], [],
    [4], [Подготовка электронной версии курсовой], [01.12.2026], [], [],
    [5], [Доработка по замечаниям при их наличии], [31.12.2026], [], [],
  )
  #v(1fr)
  #signatures
]

#let abstract-page = form[
  #form-heading[АННОТАЦИЯ НА КУРСОВУЮ РАБОТУ]
  #fields
  #v(6mm)
  #align(center)[*ХАРАКТЕРИСТИКА КУРСОВОЙ РАБОТЫ*]
  *1. Цель и задачи работы* #linebreak()
  ☐ Предложены студентами #linebreak()
  ☐ Сформулированы при участии студентов #linebreak()
  ☐ Определены руководителем

  Цель работы — разработать информационную систему мастерской и проверить защиту данных при взаимодействии пользователей с веб-сервисом.

  *2. Характер работы* #linebreak()
  ☐ Расчёт #h(1em) ☐ Конструирование #h(1em) ☒ Моделирование #linebreak()
  ☒ Другое — разработка и проверка веб-сервиса

  *4. Содержание работы* #linebreak()
  Спроектирована реляционная база данных, реализованы веб-интерфейс с тремя ролями, журналирование изменений, защита секретов и процедуры резервирования и восстановления.

  *5. Выводы* #linebreak()
  Сервис формирует интерфейс по привилегиям PostgreSQL, а журнал связывает изменения с учётной записью исполнителя. Сохранённые результаты подтверждают 49 успешных проверок сервиса и совпадение данных после восстановления до контрольной точки на отдельном стенде. Система пригодна для демонстрации механизмов защиты в учебной среде.

  #v(1fr)
  #signatures
]
