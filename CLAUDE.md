# CLAUDE.md — входной профиль для `contract-accounting`

## 1) Назначение
Это профиль для сессий с ИИ в репозитории `contract-accounting`.

## 2) Что читать в приоритете
1) `11_release_decisions_v1.md`.
2) `00_INDEX.md` и релевантные `06_roadmap.md` / `15_first_stage_completion_sequence.md`.
3) `implementation/CA-00/ADR-CA-0001-erpnext-custom-party-boundary.md` и `implementation/CA-00/ADR-CA-0002-business-replacement-technical-standalone.md`.
4) `08_open_questions.md` и `10_remaining_questions_and_actions.md`.
5) Трекинг задачи: `implementation/CA-*/README.md`, `implementation/CA-*/traceability_*.md`, `implementation/CA-*/runtime_evidence_*.md`.
6) Для кода: соответствующие тесты и quality profile `14_quality_profile_v1.md`.

## 3) Режим разработки
1) Перед кодом: понять целевые DP/OQ/REQ и точечную зону изменений.
2) Не вводить новые источники требований без записи в AGENTS-логике.
3) Если видите противоречие между источниками — остановить и запросить решение.
4) Не использовать или не предполагать secrets.
5) Для вопросов политики не писать выводов без owner evidence.

## 4) Что считать готовым
1) Код без нужных evidence и открытых gates не считается production-ready.
2) Финальная приёмка выполняется отдельным проходом с доказательной фиксацией.
3) Для документов можно редактировать без полного bench-прайса, но с обязательным описанием влияния.

## 5) Полезные ссылки проекта
1) Нормы и решения: [11_release_decisions_v1.md](11_release_decisions_v1.md)
2) ADR-кор: [implementation/CA-00](implementation/CA-00/)
3) Прогресс и очередность: [06_roadmap.md](06_roadmap.md), [10_remaining_questions_and_actions.md](10_remaining_questions_and_actions.md)
4) Доказательства: [09_verification_report.md](09_verification_report.md), [14_quality_profile_v1.md](14_quality_profile_v1.md)
