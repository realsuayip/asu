from collections.abc import Iterator
from pathlib import Path

from django.conf import settings
from django.utils import autoreload

if settings.DEBUG:
    import watchfiles
    from watchfiles.filters import PythonFilter

    BASE_DIR = Path(__file__).resolve().parent.parent

    class WatchfilesReloader(autoreload.BaseReloader):
        def tick(self) -> Iterator[None]:
            watcher = watchfiles.watch(
                BASE_DIR,
                debug=False,
                watch_filter=PythonFilter(extra_extensions=["html"]),
            )

            for file_changes in watcher:
                for _, path in file_changes:
                    self.notify_file_changed(Path(path))
                yield

    autoreload.get_reloader = WatchfilesReloader
