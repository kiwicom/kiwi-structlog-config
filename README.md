# Kiwi Structlog Config

## Installation

```bash
pip install kiwi-structlog-config
```

In your `__init__.py` add

```python
from kw.structlog_config import configure_stdlib_logging, configure_structlog


configure_structlog(debug=True)
configure_stdlib_logging(debug=True)
```

## Adding a processor

```python
from kw.structlog_config import configure_structlog, processors


anonymize = processors.Anonymize(patterns=[
    ({"visa", "amex"}, r"\d+(\d{4})", "*"*12 + r"\1"),
    ({"passenger_name"}, r"(\w)\w*", r"\1***"),
])
configure_structlog(debug=True, extra_processors=[anonymize])
```

## Testing

To run all tests:

```
tox
```
