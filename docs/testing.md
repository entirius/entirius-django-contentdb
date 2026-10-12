---
title: Testing
description: ContentDB test suite: PostgreSQL requirement and factory classes.
---

Factory classes available:

```
tests/__init__.py: AttributeSetFactory, ContentTypeFactory, ContentFactory, DraftFactory, PublishedFactory, ContentChannelFactory
```

```bash
make test                 # pytest (requires Postgres — set DATABASE_URL or use the CI default)
```
