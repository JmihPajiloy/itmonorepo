= Контрольные материалы модели <app-model>

В таблице #ref(<model-log>, supplement: [ ]) приведены результаты проверки исходной модели в SQLite. В листинге #ref(<postgres-plan>, supplement: [ ]) сохранены планы запросов PostgreSQL при отключённом последовательном сканировании.

#let model-check = json("../../lab1/verification/checks.json")
#figure(
  table(
    columns: (12mm, 1fr, 27mm),
    inset: (y: 3pt, x: 6pt),
    table.header([*№*], [*Проверка из протокола*], [*Результат*]),
    ..model-check.checks.enumerate().map(((index, check)) => (
      str(index + 1), check.test, check.result,
    )).flatten(),
  ),
  caption: [Контроль структуры и поведения исходной модели],
) <model-log>

#figure(
  raw(read("../../lab2/verification/explain.txt"), block: true),
  caption: [Планы контрольных запросов в PostgreSQL],
) <postgres-plan>

= Протокол проверки веб-сервиса <app-service>

В #ref(<service-log>, supplement: [листинге]) приведены результаты автоматической проверки ЛР4. Протокол фиксирует HTTP-ответы, отказы СУБД, число групп отчётов и проверки входа после регистрации. Снимки в основном тексте отражают отдельные сценарии работы интерфейса на учебных данных.

#figure(
  raw(read("../../lab4/verification/check.txt"), block: true),
  caption: [Сохранённый протокол автоматических проверок],
) <service-log>

= Сверка результатов восстановления <app-recovery>

В #ref(<pitr-compare>, supplement: [листинге]) приведено сравнение базы после восстановления к точке с исходным состоянием. В #ref(<latest-compare>, supplement: [листинге]) приведено сравнение копии на конец прежней линии времени с состоянием, сохранённым после тестовых изменений.

#figure(
  raw(read("../../lab5/verification/compare-before-restored.txt"), block: true),
  caption: [Сверка состояния до изменений и после восстановления],
) <pitr-compare>

#figure(
  raw(read("../../lab5/verification/compare-after-copy.txt"), block: true),
  caption: [Сверка изменённой базы с копией на конец архива],
) <latest-compare>
