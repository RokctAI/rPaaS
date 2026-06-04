# API Reference: tasks

Source file: `paas/builder/tasks.py`

## Whitelisted API Endpoints

### `def get_project_version(source_project)`
Reads and returns the version from the pubspec.yaml of a source project.

### `def generate_flutter_app(app_config_name)`
This whitelisted function is called from the client-side script.
Its only job is to enqueue the actual build task to run in the background
on a dedicated queue.

## Documented Module Functions

### `def _generate_flutter_app(app_config_name)`
This is the actual worker function that performs the build.
It is not whitelisted and is intended to be called only by the queue.
