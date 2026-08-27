# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import frappe.utils
import os
import subprocess
import json
import shutil
import urllib.request


def check_for_new_flutter_version(required_versions):
	"""
	Checks for the latest stable Flutter SDK version online and compares it
	with the version in versions.json. This is a notification-only check.
	"""
	print("\n--- Checking for Flutter SDK Updates ---")
	try:
		url = "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json"
		# Set a timeout to prevent the script from hanging indefinitely
		with urllib.request.urlopen(url, timeout=10) as response:
			data = json.loads(response.read().decode())

		current_release_hash = data.get("current_release", {}).get("stable")
		if not current_release_hash:
			print("WARNING: Could not find 'stable' release hash in the online data.")
			return

		latest_stable_version_str = None
		for release in data.get("releases", []):
			if release.get("hash") == current_release_hash:
				latest_stable_version_str = release.get("version")
				break

		if not latest_stable_version_str:
			print("WARNING: Could not determine the latest stable Flutter version from the release data.")
			return

		# Normalize versions for comparison (e.g., "v3.22.2" -> "3.22.2")
		latest_stable_version_str = latest_stable_version_str.lstrip("v")
		required_version_str = required_versions.get("flutter_sdk_version", "0.0.0").split("-")[0]

		# Compare versions numerically to handle cases like 3.10.0 vs 3.9.0
		req_parts = [int(p) for p in required_version_str.split(".")]
		latest_parts = [int(p) for p in latest_stable_version_str.split(".")]

		# Pad with zeros for safe comparison, e.g., [3, 22, 2] vs [3, 23]
		max_len = max(len(req_parts), len(latest_parts))
		req_parts.extend([0] * (max_len - len(req_parts)))
		latest_parts.extend([0] * (max_len - len(latest_parts)))

		if latest_parts > req_parts:
			print("\n" + "*" * 80)
			print(f"INFO: A newer version of the Flutter SDK is available!")
			print(f"      Latest Stable Version: {latest_stable_version_str}")
			print(f"      Your Required Version: {required_version_str}")
			print("      To upgrade, please update 'flutter_sdk_version' in your app's 'versions.json' file.")
			print("*" * 80 + "\n")
		else:
			print("INFO: Your required Flutter SDK version is up-to-date.")

	except Exception as e:
		print(
			f"WARNING: Could not check for new Flutter version online. This check will be skipped. Reason: {e}"
		)



def setup_flutter_build_tools():
	"""
	Checks for and installs a complete Flutter build environment based on versions.json.
	This is intended to run only on the control panel.
	It will skip the setup if the currently installed versions match the required versions.
	"""
	if frappe.conf.get("app_role") != "control":
		print("--- SKIPPED: Flutter Build Tools setup is only for control panel sites. ---")
		return

	# Skip if RCore is not installed
	if "rcore" not in frappe.get_installed_apps():
		print("INFO: Skipping Flutter Build Tools setup: 'rcore' app not found.")
		return

	print("--- Running Post-Install Step: Setup Flutter Build Tools ---")

	try:
		# --- 1. Version and Path Setup ---
		bench_path = frappe.utils.get_bench_path()
		sdk_dir = os.path.join(bench_path, "sdks")
		os.makedirs(sdk_dir, exist_ok=True)  # Ensure sdks dir exists

		app_path = frappe.get_app_path("rcore")
		required_versions_path = os.path.join(app_path, "versions.json")
		installed_versions_path = os.path.join(sdk_dir, ".flutter_versions_installed.json")

		with open(required_versions_path, "r") as f:
			required_versions = json.load(f)

		# --- 2. Online Version Check (Notification Only) ---
		check_for_new_flutter_version(required_versions)

		# --- 3. Version Comparison ---
		installed_versions = {}
		if os.path.exists(installed_versions_path):
			try:
				with open(installed_versions_path, "r") as f:
					installed_versions = json.load(f)
				print("INFO: Currently installed versions:")
				for key, value in installed_versions.items():
					print(f"  - {key}: {value}")
			except (json.JSONDecodeError, IOError):
				print("WARNING: Could not read installed versions file. Assuming fresh install.")
				installed_versions = {}

		print("INFO: Required versions:")
		for key, value in required_versions.items():
			print(f"  - {key}: {value}")

		if required_versions == installed_versions:
			print("\n✅ SUCCESS: Required versions are already installed and up-to-date. Skipping setup.")
			return
		else:
			print(
				"\nINFO: New versions detected or previous installation was incomplete. Proceeding with setup..."
			)

		# --- 3. Read Configuration ---
		flutter_version = required_versions["flutter_sdk_version"]
		android_platform = required_versions["android_platform"]
		android_build_tools = required_versions["android_build_tools"]
		jdk_package = required_versions["jdk_package"]

		flutter_url = f"https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_{flutter_version}.tar.xz"
		android_tools_url = (
			"https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
		)

		# --- 4. Check and Install System Dependencies ---
		print("INFO: Checking for required system dependencies...")

		deps_to_install = []
		if not shutil.which("java"):
			deps_to_install.append(jdk_package)

		other_deps = ["wget", "tar", "unzip", "clang", "cmake", "ninja-build"]
		for dep in other_deps:
			if not shutil.which(dep):
				deps_to_install.append(dep)

		if deps_to_install:
			missing_deps = ", ".join(deps_to_install)
			print(f"INFO: The following dependencies are missing: {missing_deps}. Attempting to install...")

			# --- Automated Password Handling (as per user instruction) ---
			db_root_password = None
			try:
				common_config_path = os.path.join(bench_path, "sites", "common_site_config.json")
				if os.path.exists(common_config_path):
					with open(common_config_path, "r") as f:
						common_config = json.load(f)
					db_root_password = common_config.get("db_root_password")
			except Exception as e:
				print(
					f"WARNING: Could not read database password. Will fall back to interactive prompt. Reason: {e}"
				)

			install_successful = False
			if db_root_password:
				print("INFO: Attempting automatic installation using stored password...")
				# Pass the password to sudo -S via stdin instead of embedding it
				# in a shell command string (no shell involved; keeps the secret
				# off the command line).
				update_proc = subprocess.run(
					["sudo", "-S", "apt-get", "update", "-y"],
					input=db_root_password + "\n",
					capture_output=True,
					text=True,
				)
				if update_proc.returncode == 0:
					install_proc = subprocess.run(
						["sudo", "-S", "apt-get", "install", "-y"] + deps_to_install,
						input=db_root_password + "\n",
						capture_output=True,
						text=True,
					)
					if install_proc.returncode == 0:
						install_successful = True
						print("SUCCESS: Automatic installation of system dependencies was successful.")
					else:
						print(
							"WARNING: Automatic installation failed. The provided password might be incorrect."
						)
						print(f"         Stderr: {install_proc.stderr.strip()}")
				else:
					print(
						"WARNING: Automatic repository update failed. The provided password might be incorrect."
					)
					print(f"         Stderr: {update_proc.stderr.strip()}")

			if not install_successful:
				print("INFO: Falling back to standard interactive password prompt for installation.")
				try:
					# Run commands interactively, allowing user to see prompts.
					subprocess.run(["sudo", "apt-get", "update", "-y"], check=True)
					subprocess.run(["sudo", "apt-get", "install", "-y"] + deps_to_install, check=True)
					print("SUCCESS: All system dependencies installed via interactive prompt.")
				except (subprocess.CalledProcessError, Exception) as e:
					error_detail = e.stderr.decode() if hasattr(e, "stderr") else e
					print(f"\nERROR: Interactive installation of system dependencies failed. Stderr: {error_detail}")
					print(f"Please install the following packages manually: {', '.join(deps_to_install)}")
					return
		else:
			print("SUCCESS: All system dependencies are present.")

		# --- 5. Setup SDK Directories ---
		flutter_sdk_path = os.path.join(sdk_dir, "flutter")
		android_sdk_path = os.path.join(sdk_dir, "android")

		# --- 6. Install Flutter SDK ---
		# This is a destructive but reliable way to ensure the correct version
		# is installed.
		print(f"INFO: Ensuring Flutter SDK version {flutter_version} is installed...")
		if os.path.exists(flutter_sdk_path):
			shutil.rmtree(flutter_sdk_path)

		archive = os.path.join(sdk_dir, "flutter.tar.xz")
		subprocess.run(["wget", "-q", "-O", archive, flutter_url], check=True)
		subprocess.run(["tar", "-xf", archive, "-C", sdk_dir], check=True, stdout=subprocess.DEVNULL)
		os.remove(archive)
		print("SUCCESS: Flutter SDK installed.")

		# --- 7. Install Android SDK ---
		sdkmanager_path = os.path.join(android_sdk_path, "cmdline-tools", "latest", "bin", "sdkmanager")
		# This is a destructive but reliable way to ensure the correct version
		# is installed.
		print("INFO: Ensuring Android command-line tools are installed...")
		if os.path.exists(os.path.join(android_sdk_path, "cmdline-tools")):
			shutil.rmtree(os.path.join(android_sdk_path, "cmdline-tools"))

		archive = os.path.join(sdk_dir, "android-tools.zip")
		subprocess.run(["wget", "-q", "-O", archive, android_tools_url], check=True)
		temp_extract_path = os.path.join(sdk_dir, "android-temp")
		os.makedirs(temp_extract_path, exist_ok=True)
		shutil.unpack_archive(archive, temp_extract_path)

		tools_latest_path = os.path.join(android_sdk_path, "cmdline-tools", "latest")
		os.makedirs(tools_latest_path, exist_ok=True)
		extracted_dir = os.path.join(temp_extract_path, "cmdline-tools")
		for item in os.listdir(extracted_dir):
			shutil.move(os.path.join(extracted_dir, item), os.path.join(tools_latest_path, item))

		os.remove(archive)
		shutil.rmtree(temp_extract_path)

		# Grant execute permissions to the sdkmanager to prevent exit code 126
		if os.path.exists(sdkmanager_path):
			os.chmod(sdkmanager_path, 0o755)

		print("SUCCESS: Android command-line tools installed.")

		# --- 8. Install Android Packages ---
		env = os.environ.copy()
		env["ANDROID_HOME"] = android_sdk_path
		env["FLUTTER_HOME"] = flutter_sdk_path
		flutter_bin = os.path.join(flutter_sdk_path, "bin")
		platform_tools = os.path.join(android_sdk_path, "platform-tools")
		env["PATH"] = f"{flutter_bin}:{os.path.dirname(sdkmanager_path)}:{platform_tools}:{env['PATH']}"

		print("INFO: Installing required Android SDK packages and accepting licenses...")
		packages_to_install = [
			"platform-tools",
			f"platforms;android-{android_platform}",
			f"build-tools;{android_build_tools}",
		]
		# Feed repeated "y" answers on stdin instead of piping from `yes`
		# through a shell (no shell involved; the license prompts are finite).
		subprocess.run(
			[sdkmanager_path, "--licenses"],
			input=b"y\n" * 100,
			env=env,
			check=True,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.PIPE,
		)
		for package in packages_to_install:
			subprocess.run(
				[sdkmanager_path, package],
				env=env,
				check=True,
				stdout=subprocess.DEVNULL,
				stderr=subprocess.PIPE,
			)
		print("SUCCESS: All Android SDK packages installed and licenses accepted.")

		# --- 9. Configure User's PATH ---
		print("INFO: Configuring user's PATH in ~/.bashrc...")
		try:
			import pwd

			uid = os.stat(bench_path).st_uid
			user_info = pwd.getpwuid(uid)
			home_dir = user_info.pw_dir
			bashrc_path = os.path.join(home_dir, ".bashrc")

			exports = [
				f"\n# ROKCT Build Environment",
				f'export ANDROID_HOME="{android_sdk_path}"',
				f'export FLUTTER_HOME="{flutter_sdk_path}"',
				f'export PATH="$FLUTTER_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"',
			]

			if not os.path.exists(bashrc_path):
				open(bashrc_path, "a").close()
				os.chown(bashrc_path, uid, user_info.pw_gid)
				print(f"INFO: ~/.bashrc not found. Created a new one at {bashrc_path}")

			with open(bashrc_path, "r+") as f:
				content = f.read()
				if exports[0] not in content:
					f.write("\n".join(exports) + "\n")
					print(f"SUCCESS: PATH variables added to {bashrc_path}.")
				else:
					print(f"INFO: PATH variables already exist in {bashrc_path}.")

		except (ImportError, KeyError, OSError) as e:
			print(f"WARNING: Could not automatically update shell configuration. Reason: {e}")
			print("Please add the following lines to your shell configuration file (e.g., ~/.bashrc):")
			print("\n".join(exports))

		# --- 10. Final Verification ---
		print("INFO: Running 'flutter doctor' to verify installation...")
		doctor_process = subprocess.run(
			[os.path.join(flutter_sdk_path, "bin", "flutter"), "doctor"],
			capture_output=True,
			text=True,
			env=env,
		)
		doctor_output = doctor_process.stdout

		if "[✓] Android toolchain" in doctor_output:
			print("SUCCESS: Flutter doctor reports a healthy Android toolchain.")
		else:
			print("WARNING: Flutter doctor reported issues. Please review the output below:")
			print(doctor_output)

		print("\n" + "=" * 80)
		print("✅ SUCCESS: Flutter and Android build tools are installed and ready for the system.")
		print("\nIMPORTANT: To apply the new environment variables, you must either:")
		print("  1. Close and reopen your terminal session.")
		print("  2. Run the command: source ~/.bashrc")
		print("=" * 80)

		# --- 11. Create/Update Lock File ---
		with open(installed_versions_path, "w") as f:
			json.dump(required_versions, f, indent=4)
		print(f"INFO: Updated version lock file at {installed_versions_path}")

	except Exception as e:
		print(f"\nFATAL ERROR during Flutter setup: {e}")
		import traceback

		traceback.print_exc()
		frappe.log_error(message=frappe.get_traceback(), title="Flutter Build Tools Setup Error")
