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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import os
import json
import subprocess
import shutil
import frappe


@frappe.whitelist()
def fetch_paas_sources():
	"""
	Reads paas_source_versions.json and fetches/updates Flutter source code
	into the builder/source_code directory of rcore (or legacy paas).
	"""
	try:
		# paas is merged into rcore; prefer rcore, fall back to legacy paas
		app = next((a for a in ("rcore", "paas") if a in frappe.get_installed_apps()), None)
		if app is None:
			print("Neither rcore nor paas is installed. Skipping source fetch.")
			return

		# Path to paas_source_versions.json
		this_dir = os.path.dirname(__file__)
		config_path = os.path.join(this_dir, "paas_source_versions.json")

		if not os.path.exists(config_path):
			print(f"Config file not found: {config_path}")
			return

		with open(config_path, "r") as f:
			sources = json.load(f)

		# Target directory: <app>/<app>/builder/source_code
		source_code_base = frappe.get_app_path(app, "builder", "source_code")

		if not os.path.exists(source_code_base):
			os.makedirs(source_code_base, exist_ok=True)

		for app_name, config in sources.items():
			owner = config.get("owner")
			# Use SSH for private repos to avoid password prompts (assumes SSH
			# keys are setup)
			repo_url = f"git@github.com:{owner}/{app_name}.git"

			target_path = os.path.join(source_code_base, app_name)

			# Nuke & Pave Strategy
			if os.path.exists(target_path):
				print(f"Removing existing {app_name} for fresh clone...")
				shutil.rmtree(target_path)

			print(f"Fetching tags for {app_name}...")
			try:
				# Use git ls-remote to get tags without cloning first (uses system auth)
				# Sort by version descending to get latest first
				cmd = ["git", "ls-remote", "--tags", "--refs", "--sort=-v:refname", repo_url]

				# Prevent interactive prompts and set timeout
				env = os.environ.copy()
				env["GIT_TERMINAL_PROMPT"] = "0"

				result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60, env=env)

				latest_valid_tag = None

				for line in result.stdout.splitlines():
					# Output format: <hash>	refs/tags/<tag_name>
					parts = line.split()
					if len(parts) < 2:
						continue

					ref = parts[1]
					tag_name = ref.replace("refs/tags/", "")

					# Filter Logic (Mimicking installer.py + dev check)
					# Ignore unstable releases
					t_low = tag_name.lower()
					if any(x in t_low for x in ["beta", "rc", "alpha", "hotfix", "-dev"]):
						continue

					# Found the latest valid tag (since list is sorted
					# descending)
					latest_valid_tag = tag_name
					break

				if latest_valid_tag:
					print(f"[{app_name}] Found latest production release: {latest_valid_tag}")

					# Nuke & Pave Strategy
					if os.path.exists(target_path):
						print(f"Removing existing {app_name} for fresh clone...")
						shutil.rmtree(target_path)

					print(f"Downloading {app_name} ({latest_valid_tag})...")
					# Clone specifically the tag, with depth 1 (lightweight,
					# like downloading a zip)
					subprocess.run(
						["git", "clone", "--branch", latest_valid_tag, "--depth", "1", repo_url, target_path],
						check=True,
					)
				else:
					print(f"[{app_name}] No valid production tag found. Skipping.")

			except subprocess.CalledProcessError as e:
				print(f"Error fetching tags for {app_name}: {e}")
			except Exception as e:
				print(f"Error processing {app_name}: {e}")

		print("PaaS sources fetch complete.")

	except Exception as e:
		frappe.log_error(f"Error fetching PaaS sources: {e}")
		print(f"Error fetching PaaS sources: {e}")

