#!/usr/bin/env python3
"""Local sanity checks for .github/workflows before pushing CI changes.

Checks that GitHub will otherwise only tell you about after a run starts:
  1. every workflow file parses as YAML
  2. every `needs:` reference in build-release.yml resolves to a real job
  3. every input passed to the reusable build-firmware.yml is actually declared
  4. no two build jobs publish the same artifact name
  5. the publish/release gates wait on every build job

Usage:  python3 .ai-workflow/validate-workflows.py
Exits non-zero if any check fails.
"""
import glob
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOWS = os.path.join(os.path.dirname(HERE), ".github", "workflows")

failures = []


def check(condition, label, detail=""):
    print("  [%s] %s%s" % ("OK" if condition else "FAIL", label,
                           "" if condition else "  -> %s" % detail))
    if not condition:
        failures.append(label)


def main():
    docs = {}
    print("YAML syntax")
    for path in sorted(glob.glob(os.path.join(WORKFLOWS, "*.yml"))):
        name = os.path.basename(path)
        try:
            with open(path) as fh:
                docs[name] = yaml.safe_load(fh)
        except Exception as exc:  # noqa: BLE001 - report and continue
            check(False, name, exc)
    if failures:
        return 1
    print("  [OK] %d workflow files parsed" % len(docs))

    rel = docs["build-release.yml"]
    jobs = rel["jobs"]
    build_jobs = [n for n, j in jobs.items() if "uses" in j]

    print("\nneeds: references resolve")
    for name, job in jobs.items():
        for dep in job.get("needs") or []:
            check(dep in jobs, "%s needs %s" % (name, dep), "no such job")

    # PyYAML parses a bare `on:` key as the boolean True.
    build_fw = docs["build-firmware.yml"]
    trigger = build_fw.get("on", build_fw.get(True))
    declared = set(trigger["workflow_call"]["inputs"].keys())

    print("\nreusable-workflow inputs are declared")
    for name in build_jobs:
        passed = set((jobs[name].get("with") or {}).keys())
        unknown = sorted(passed - declared)
        check(not unknown, name, "undeclared inputs: %s" % unknown)

    print("\nartifact names are unique across build jobs")
    seen = {}
    for name in build_jobs:
        with_ = jobs[name].get("with") or {}
        names = ["firmware-%s" % with_["board"], "build-log-%s" % with_["board"]]
        if with_.get("releasepackages"):
            names.append("packages-targets-%s--%s"
                         % (with_["target"], with_["subtarget"]))
            if with_.get("cpu_arch"):
                names.append("packages-arch-%s" % with_["cpu_arch"])
        for artifact in names:
            seen.setdefault(artifact, []).append(name)
    for artifact, owners in sorted(seen.items()):
        check(len(owners) == 1, artifact, "produced by %s" % owners)

    print("\nrelease gates wait on every build job")
    for gate in ("publish-packages", "release"):
        needs = jobs[gate].get("needs") or []
        missing = [b for b in build_jobs if b not in needs]
        check(not missing, gate, "missing: %s" % missing)

    print("\n%s" % ("FAILURES: %s" % failures if failures else "All checks passed."))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
