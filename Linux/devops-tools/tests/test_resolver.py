"""Offline contract tests for supply-chain validation and upstream metadata formats."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

RESOLVER = Path(__file__).resolve().parents[1] / "roles/devops_tools/files/resolve_artifact.py"
SPEC = importlib.util.spec_from_file_location("resolver", RESOLVER)
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)
SHA = "a" * 64


class IntegrityTests(unittest.TestCase):
    def test_checksum_selects_exact_asset(self):
        text = "b" * 64 + "  other.tar.gz\n" + SHA + " *wanted.tar.gz\n"
        self.assertEqual(resolver.checksum(text, "wanted.tar.gz"), SHA)

    def test_missing_checksum_fails_closed(self):
        with self.assertRaises(ValueError):
            resolver.checksum(SHA + " other.zip", "wanted.zip")

    def test_weak_checksum_rejected(self):
        with self.assertRaises(ValueError):
            resolver.checksum("a" * 32 + " wanted.zip", "wanted.zip")

    def test_malformed_digest_rejected(self):
        with self.assertRaises(ValueError):
            resolver.descriptor("1.2.3", "https://example.com/file", "bad", "raw", "tool")

    def test_insecure_url_rejected(self):
        with self.assertRaises(ValueError):
            resolver.descriptor("1.2.3", "http://example.com/file", SHA, "raw", "tool")

    def test_metadata_http_rejected_before_network(self):
        with self.assertRaises(ValueError):
            resolver.fetch("http://example.com/metadata")

    def test_archive_path_traversal_rejected(self):
        for member in ("../bin/tool", "/bin/tool", "dir/../../tool"):
            with self.subTest(member=member), self.assertRaises(ValueError):
                resolver.descriptor("1.2.3", "https://example.com/file", SHA, "tar", member)

    def test_prerelease_descriptor_rejected(self):
        with self.assertRaises(ValueError):
            resolver.descriptor("1.2.3-rc1", "https://example.com/file", SHA, "raw", "tool")

    def test_aws_signature_requires_https(self):
        with self.assertRaises(ValueError):
            resolver.validate(dict(version="2.1.0", url="https://example.com/file", format="aws",
                                   member="aws/install", signature_url="http://example.com/sig"))


class ResolutionTests(unittest.TestCase):
    @patch.object(resolver, "fetch")
    def test_latest_kubectl_normalizes_version(self, fetch):
        fetch.side_effect = ["v1.35.1\n", SHA + "\n"]
        artifact = resolver.resolve("kubectl", "latest")
        self.assertEqual(artifact["version"], "1.35.1")
        self.assertEqual(artifact["sha256"], SHA)
        self.assertIn("/v1.35.1/bin/linux/amd64/kubectl", artifact["url"])

    @patch.object(resolver, "fetch", return_value=SHA)
    def test_pinned_kubectl_does_not_query_latest(self, fetch):
        artifact = resolver.resolve("kubectl", "v1.34.2")
        self.assertEqual(artifact["version"], "1.34.2")
        fetch.assert_called_once_with(artifact["url"] + ".sha256")

    @patch.object(resolver, "fetch")
    @patch.object(resolver, "read_json")
    def test_node_lts_skips_current(self, read_json, fetch):
        read_json.return_value = [{"version": "v25.1.0", "lts": False}, {"version": "v24.1.0", "lts": "Krypton"}]
        fetch.return_value = SHA + "  node-v24.1.0-linux-x64.tar.gz"
        artifact = resolver.resolve("nodejs", "lts")
        self.assertEqual(artifact["version"], "24.1.0")
        self.assertEqual(artifact["member"], "node-v24.1.0-linux-x64/bin/node")

    @patch.object(resolver, "read_json")
    def test_go_selects_linux_amd64_archive(self, read_json):
        release = dict(version="go1.24.1", stable=True, files=[
            dict(os="darwin", arch="amd64", kind="archive", filename="wrong", sha256=SHA),
            dict(os="linux", arch="amd64", kind="archive", filename="go1.24.1.linux-amd64.tar.gz", sha256=SHA)])
        read_json.side_effect = [[release], [release]]
        artifact = resolver.resolve("go", "latest")
        self.assertTrue(artifact["url"].endswith("linux-amd64.tar.gz"))

    @patch.object(resolver, "read_json", return_value={"draft": False, "prerelease": True})
    def test_prerelease_github_rejected(self, _):
        with self.assertRaises(ValueError):
            resolver.release("helm/helm", "latest")

    @patch.object(resolver, "release")
    def test_github_digest_required_for_yq(self, release):
        release.return_value = dict(tag_name="v4.1.0", assets=[dict(name="yq_linux_amd64", browser_download_url="https://example.com/yq")])
        with self.assertRaises(ValueError):
            resolver.resolve("yq", "latest")

    @patch.object(resolver, "release")
    def test_yq_verified_digest(self, release):
        release.return_value = dict(tag_name="v4.1.0", assets=[dict(name="yq_linux_amd64", browser_download_url="https://example.com/yq", digest="sha256:" + SHA)])
        artifact = resolver.resolve("yq", "latest")
        self.assertEqual(artifact["format"], "raw")
        self.assertEqual(artifact["sha256"], SHA)

    @patch.object(resolver, "fetch")
    @patch.object(resolver, "release")
    def test_github_cli_checksum_fallback(self, release, fetch):
        release.return_value = dict(tag_name="v2.1.0", assets=[
            dict(name="gh_2.1.0_linux_amd64.tar.gz", browser_download_url="https://example.com/gh"),
            dict(name="gh_2.1.0_checksums.txt", browser_download_url="https://example.com/sums")])
        fetch.return_value = SHA + " gh_2.1.0_linux_amd64.tar.gz"
        self.assertEqual(resolver.resolve("github_cli", "latest")["sha256"], SHA)

    @patch.object(resolver, "fetch")
    def test_aws_v2_version_and_html_key(self, fetch):
        fetch.side_effect = ["2.27.1\n======\n", "<pre>-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n abc\n-----END PGP PUBLIC KEY BLOCK-----</pre>"]
        artifact = resolver.resolve("awscli", "latest")
        self.assertEqual(artifact["format"], "aws")
        self.assertTrue(artifact["signature_url"].endswith("2.27.1.zip.sig"))
        self.assertIn("\nabc\n", artifact["public_key"])

    def test_aws_v1_rejected(self):
        with self.assertRaises(ValueError):
            resolver.resolve("awscli", "1.20.0")

    @patch.object(resolver, "read_json")
    def test_latest_python_package_is_not_silently_downgraded(self, read_json):
        read_json.return_value = {"info": {"version": "25.1.0", "requires_python": ">=3.12"}}
        artifact = resolver.resolve("ansible_lint", "latest", "https://mirror.example.com/pypi")
        self.assertEqual(artifact["version"], "25.1.0")
        self.assertEqual(artifact["requires_python"], ">=3.12")
        read_json.assert_called_once_with("https://mirror.example.com/pypi/ansible-lint/json")


if __name__ == "__main__":
    unittest.main()
