"""Portable static checks; these are not Ansible execution/integration tests."""

import re
import json
from pathlib import Path
import unittest

import yaml
from jinja2 import Environment
from jinja2.nativetypes import NativeEnvironment

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "roles/devops_tools/tasks"


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("Duplicate YAML key: " + str(key))
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load(path):
    return yaml.load(path.read_text(), Loader=UniqueKeyLoader)


def task_value(filename, name, key):
    tasks = load(TASKS / filename)
    return next(t for t in tasks if t["name"] == name)["ansible.builtin.set_fact"][key]


class StaticTests(unittest.TestCase):
    def test_all_yaml_has_unique_keys(self):
        for path in ROOT.rglob("*.yml"):
            with self.subTest(path=path):
                load(path)

    def test_every_catalog_kind_has_tasks(self):
        defaults = load(ROOT / "roles/devops_tools/defaults/main.yml")
        for name, tool in defaults["devops_catalog"].items():
            with self.subTest(tool=name):
                self.assertTrue((TASKS / (tool["kind"] + ".yml")).is_file())
                self.assertTrue(tool["args"])

    def test_example_tools_and_versions_are_known(self):
        defaults = load(ROOT / "roles/devops_tools/defaults/main.yml")
        example = load(ROOT / "config.example.yml")
        self.assertFalse(set(example["devops_selected_tools"]) - set(defaults["devops_catalog"]))
        self.assertFalse(set(example["devops_versions"]) - set(defaults["devops_default_versions"]))
        self.assertEqual(defaults["devops_selected_tools"], [])
        self.assertFalse(defaults["devops_upgrade_existing"])

    def test_jinja_templates_parse(self):
        env = Environment()

        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    visit(key)
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, str) and ("{{" in value or "{%" in value):
                env.parse(value)

        for path in ROOT.rglob("*.yml"):
            with self.subTest(path=path):
                visit(load(path))

    def test_all_tasks_have_names_and_one_fqcn_action(self):
        def visit(tasks):
            for task in tasks:
                self.assertIn("name", task)
                actions = [key for key in task if key.startswith("ansible.builtin.")]
                if "block" in task:
                    self.assertFalse(actions)
                    for key in ("block", "rescue", "always"):
                        visit(task.get(key, []))
                else:
                    self.assertEqual(len(actions), 1, task["name"])

        for path in TASKS.glob("*.yml"):
            with self.subTest(path=path):
                visit(load(path))

    def test_no_error_suppression(self):
        for path in TASKS.glob("*.yml"):
            text = path.read_text()
            self.assertNotIn("ignore_errors", text)
            self.assertNotIn("failed_when: false", text)


class PolicyTests(unittest.TestCase):
    def test_transient_failures_retry_and_permanent_failures_stop(self):
        expression = next(t for t in load(TASKS / 'binary.yml') if t['name'].startswith('Resolve exact'))['until']
        defaults = load(ROOT / 'roles/devops_tools/defaults/main.yml')
        env = NativeEnvironment()
        env.tests['succeeded'] = lambda value: not value.get('failed', False)
        env.filters['to_json'] = json.dumps
        env.filters['regex_search'] = lambda value, pattern: (m.group(0) if (m := re.search(pattern, value)) else None)
        for message, failed, stop in [('connection timed out', True, False),
                                      ('checksum mismatch', True, True),
                                      ('HTTP Error 404: Not Found', True, True),
                                      ('HTTP Error 503: Unavailable', True, False),
                                      ('download successful', False, True)]:
            with self.subTest(message=message):
                result = env.from_string('{{ ' + expression + ' }}').render(
                    devops_resolution={'failed': failed, 'msg': message},
                    devops_transient_error_pattern=defaults['devops_transient_error_pattern'])
                self.assertIs(result, stop)

    def test_existing_latest_lts_system_are_preserved(self):
        expression = task_value("tool.yml", "Determine whether to manage this tool", "devops_manage")
        env = NativeEnvironment()
        for requested in ("latest", "lts", "system"):
            with self.subTest(requested=requested):
                result = env.from_string(expression).render(devops_current={"path": "/usr/bin/tool"},
                                                            devops_upgrade_existing=False, devops_requested=requested)
                self.assertIs(result, False)

    def test_missing_tool_is_installed(self):
        expression = task_value("tool.yml", "Determine whether to manage this tool", "devops_manage")
        result = NativeEnvironment().from_string(expression).render(devops_current={"path": None},
                                                                    devops_upgrade_existing=False, devops_requested="latest")
        self.assertIs(result, True)

    def test_pin_or_upgrade_authorizes_management(self):
        expression = task_value("tool.yml", "Determine whether to manage this tool", "devops_manage")
        for upgrade, requested in ((False, "1.2.3"), (True, "latest")):
            result = NativeEnvironment().from_string(expression).render(devops_current={"path": "/usr/bin/tool"},
                                                                        devops_upgrade_existing=upgrade, devops_requested=requested)
            self.assertIs(result, True)

    def test_version_match_requires_complete_version(self):
        expression = task_value("binary.yml", "Compare installed and requested version", "devops_binary_matches")
        env = NativeEnvironment()
        env.filters["regex_escape"] = re.escape
        env.filters["regex_search"] = lambda value, pattern: (m.group(0) if (m := re.search(pattern, value)) else None)
        for current, desired, expected in (("v1.2.3", "1.2.3", True), ("v1.2.30", "1.2.3", False),
                                            ("v1.2.3-rc1", "1.2.3", False), ("go1.2.3rc1", "1.2.3", False),
                                            ("aws-cli/2.27.1 Python/3.13", "2.27.1", True),
                                            ('{"gitVersion":"v1.35.1"}', "1.35.1", True)):
            with self.subTest(current=current, desired=desired):
                result = env.from_string(expression).render(devops_current={"path": "/usr/local/bin/tool", "version": current},
                                                            devops_artifact={"version": desired})
                self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()
