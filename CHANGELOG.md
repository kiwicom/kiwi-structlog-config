# CHANGELOG

## 0.3.5 (2025-07-18)

- add support for ddtrace==3.10

## 0.3.4 (2024-09-27)

- Remove `__init__.py` from kw folder

## 0.3.3 (2024-01-24)

- Add support for structlog==24.1.0

## 0.3.2 (2023-03-07)

- ddtrace: use ddtrace.Tracer.get_log_correlation_context()
  instead of deprecated ddtrace.helpers.get_correlation_ids.
  ddtrace above version v0.53.0 required for this to work.

## 0.3.1 (2023-03-07)

- Move JSONRenderer to be last processor in the list:

  > JSONRenderer processors flattens event_dict to string
  > and it cannot be used by following processors.
  > Let's move extra_processors before
  > JSONRenderer processor to have original dict available.

## 0.3.0 (2023-03-01)

- Take ownership from platform team to booking backend team
- Remove support for Python versions 2.7, 3.6, 3.7 and 3.8
- Add support for Python versions 3.9, 3.10 and 3.11
- Upgrade Python requirements
- Remove pkg_resources declaration
- Remove coala
- Add pre-commit
- Replace pylint with ruff
- Remove unused more-itertools

## 0.1.1 (2018-03-14)

Make imports more concise

## 0.1.0 (2018-01-15)

Initial release.
