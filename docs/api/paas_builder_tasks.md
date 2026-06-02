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

### `def log_message(message, app_config_name)`
Helper function to append messages to the build log.

### `def get_original_package_name(temp_dir)`
Reads the original package name from the android/app/build.gradle file.

### `def rename_android_package_structure(temp_dir, old_package_name, new_package_name, app_config_name)`
Renames the android package directory structure.

### `def get_windows_exe_name(temp_dir)`
Reads the BINARY_NAME from the windows/runner/CMakeLists.txt file.

### `def modify_project_files(temp_dir, app_config)`
Modifies the files in the temporary Flutter project directory
based on the app configuration.

### `def handle_custom_font(temp_dir, app_config)`
Handles the uploaded custom font file.

### `def replace_image_asset(temp_dir, app_config, field_name, target_path_relative)`
Replaces a specified image asset in the project with an uploaded file.

### `def update_splash_screen(temp_dir, app_config, settings)`
Updates the native splash screen configuration.

### `def run_gitops_compilation(app_config, source_project)`
Performs fully offloaded GitOps compilation of Flutter apps.
Saves environment settings and Google Services JSON to Monorepo via GitHub API,
then triggers a custom branch refs push on target repository to run CI/CD.

### `def _generate_flutter_app(app_config_name)`
This is the actual worker function that performs the build.
It is not whitelisted and is intended to be called only by the queue.
