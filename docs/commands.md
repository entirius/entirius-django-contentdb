---
title: Management Commands
description: ContentDB management commands: channel and language sync, channel propagation, image optimization.
---

```bash
# Sync commands (run inside Django service context)
python manage.py sync_contentdb_channels    # Sync from PIM
python manage.py sync_contentdb_languages   # Sync from django_regional
python manage.py propagate_content_channels --channel=default  # Assign channel to public content
```

Image optimization:

```bash
python manage.py images-optimize   # Optimize/Re-optimize all images
```
