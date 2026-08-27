# Realized sample counts

|                                 |   control |   event |
|:--------------------------------|----------:|--------:|
| ('destructive_wind', 'dev')     |      4110 |    2055 |
| ('destructive_wind', 'holdout') |       822 |     412 |
| ('flash_flood', 'dev')          |      2944 |    1472 |
| ('flash_flood', 'holdout')      |      1054 |     528 |
| ('flood', 'dev')                |      4858 |    2429 |
| ('flood', 'holdout')            |       538 |     269 |
| ('tornado', 'dev')              |      3174 |    1587 |
| ('tornado', 'holdout')          |      1040 |     520 |

- total series: 27812 (9272 events, 18540 controls)
- relaxed-constraint controls: 102; unfilled control slots: 4

Events by class x cohort:

| event_class      |   dev |   holdout |
|:-----------------|------:|----------:|
| destructive_wind |  2055 |       412 |
| flash_flood      |  1472 |       528 |
| flood            |  2429 |       269 |
| tornado          |  1587 |       520 |
