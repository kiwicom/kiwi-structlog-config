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

## Testing

To run all tests:

```
tox
```
