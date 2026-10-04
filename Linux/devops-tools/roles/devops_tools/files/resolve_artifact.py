"""Resolve official Linux AMD64 artifacts; emit metadata, never execute downloads.

Only TLS-authenticated upstream SHA256 values or AWS PGP signatures are accepted.
Used by Ansible on the managed Linux host; standard library only, Python >=3.9.
"""

import argparse
import html
import json
import re
import sys
import urllib.request
from urllib.parse import urlparse


def fetch(url):
    if urlparse(url).scheme != "https":
        raise ValueError("Metadata URLs must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "devops-tools-ansible/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        if urlparse(response.geturl()).scheme != "https":
            raise ValueError("Refusing HTTPS downgrade")
        return response.read().decode("utf-8")


def read_json(url):
    return json.loads(fetch(url))


def checksum(text, filename):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename:
            if re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                return parts[0].lower()
    raise ValueError("No SHA256 checksum for " + filename)


def release(repo, version):
    suffix = "latest" if version == "latest" else "tags/v" + version
    result = read_json("https://api.github.com/repos/" + repo + "/releases/" + suffix)
    if result.get("draft") or result.get("prerelease"):
        raise ValueError("Only stable published releases are accepted")
    return result


def descriptor(version, url, digest, fmt, member):
    return validate(dict(version=version, url=url, sha256=digest, format=fmt, member=member))


def validate(value):
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value["version"]):
        raise ValueError("Artifact requires an exact stable version")
    if urlparse(value["url"]).scheme != "https":
        raise ValueError("Artifact URL must use HTTPS")
    if value["format"] not in ("raw", "tar", "zip", "aws"):
        raise ValueError("Unknown artifact format")
    if not re.fullmatch(r"[A-Za-z0-9_./+-]+", value["member"]) or ".." in value["member"].split("/") or value["member"].startswith("/"):
        raise ValueError("Unsafe archive member")
    if value["format"] == "aws":
        if urlparse(value["signature_url"]).scheme != "https":
            raise ValueError("AWS signature URL must use HTTPS")
        if not value.get("public_key", "").startswith("-----BEGIN PGP PUBLIC KEY BLOCK-----"):
            raise ValueError("AWS public key missing")
    elif not re.fullmatch(r"[0-9a-fA-F]{64}", value["sha256"]):
        raise ValueError("A SHA256 digest is mandatory")
    return value


def resolve(tool, requested, python_index="https://pypi.org/pypi"):
    version = requested.removeprefix("v")
    if tool in ("ansible", "ansible_lint", "pipx"):
        package = "ansible-lint" if tool == "ansible_lint" else tool
        suffix = "/json" if version == "latest" else "/" + version + "/json"
        metadata = read_json(python_index.rstrip("/") + "/" + package + suffix)
        return {"version": metadata["info"]["version"], "requires_python": metadata["info"].get("requires_python", "")}
    if tool == "kubectl":
        if version == "latest":
            version = fetch("https://dl.k8s.io/release/stable.txt").strip().removeprefix("v")
        url = "https://dl.k8s.io/release/v" + version + "/bin/linux/amd64/kubectl"
        return descriptor(version, url, fetch(url + ".sha256").strip(), "raw", "kubectl")
    if tool == "go":
        if version == "latest":
            version = read_json("https://go.dev/dl/?mode=json")[0]["version"].removeprefix("go")
        releases = read_json("https://go.dev/dl/?mode=json&include=all")
        artifact = next(f for r in releases if r["version"] == "go" + version and r["stable"]
                        for f in r["files"] if f["os"] == "linux" and f["arch"] == "amd64" and f["kind"] == "archive")
        return descriptor(version, "https://go.dev/dl/" + artifact["filename"], artifact["sha256"], "tar", "go/bin/go")
    if tool == "nodejs":
        if version in ("latest", "lts"):
            versions = read_json("https://nodejs.org/dist/index.json")
            version = next(v["version"].removeprefix("v") for v in versions
                           if version == "latest" or v["lts"])
        filename = "node-v" + version + "-linux-x64.tar.gz"
        base = "https://nodejs.org/dist/v" + version + "/"
        return descriptor(version, base + filename, checksum(fetch(base + "SHASUMS256.txt"), filename),
                          "tar", "node-v" + version + "-linux-x64/bin/node")
    if tool == "terraform":
        if version == "latest":
            version = read_json("https://checkpoint-api.hashicorp.com/v1/check/terraform")["current_version"]
        filename = "terraform_" + version + "_linux_amd64.zip"
        base = "https://releases.hashicorp.com/terraform/" + version + "/"
        sums = fetch(base + "terraform_" + version + "_SHA256SUMS")
        return descriptor(version, base + filename, checksum(sums, filename), "zip", "terraform")
    if tool == "helm":
        metadata = release("helm/helm", version)
        version = metadata["tag_name"].removeprefix("v")
        url = "https://get.helm.sh/helm-v" + version + "-linux-amd64.tar.gz"
        return descriptor(version, url, fetch(url + ".sha256sum").split()[0], "tar", "linux-amd64/helm")
    if tool in ("yq", "trivy", "github_cli", "shellcheck"):
        repo = {"yq": "mikefarah/yq", "trivy": "aquasecurity/trivy", "github_cli": "cli/cli", "shellcheck": "koalaman/shellcheck"}[tool]
        metadata = release(repo, version)
        version = metadata["tag_name"].removeprefix("v")
        name = {"yq": "yq_linux_amd64", "trivy": "trivy_" + version + "_Linux-64bit.tar.gz",
                "github_cli": "gh_" + version + "_linux_amd64.tar.gz",
                "shellcheck": "shellcheck-v" + version + ".linux.x86_64.tar.xz"}[tool]
        asset = next(a for a in metadata["assets"] if a["name"] == name)
        digest = asset.get("digest") or ""
        if digest.startswith("sha256:"):
            digest = digest.split(":", 1)[1]
        elif tool in ("trivy", "github_cli"):
            sums_name = ("trivy_" if tool == "trivy" else "gh_") + version + "_checksums.txt"
            sums = next(a for a in metadata["assets"] if a["name"] == sums_name)
            digest = checksum(fetch(sums["browser_download_url"]), name)
        else:
            raise ValueError("Release lacks a GitHub SHA256 digest; provide a verified artifact override")
        member = {"yq": "yq", "trivy": "trivy", "github_cli": "gh_" + version + "_linux_amd64/bin/gh",
                  "shellcheck": "shellcheck-v" + version + "/shellcheck"}[tool]
        return descriptor(version, asset["browser_download_url"], digest, "raw" if tool == "yq" else "tar", member)
    if tool == "awscli":
        if version == "latest":
            log = fetch("https://raw.githubusercontent.com/aws/aws-cli/v2/CHANGELOG.rst")
            version = re.search(r"(?m)^([2]\.[0-9]+\.[0-9]+)\s*$", log).group(1)
        if not version.startswith("2."):
            raise ValueError("Only AWS CLI v2 is supported")
        page = fetch("https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        plain = html.unescape(re.sub(r"<[^>]+>", "", page))
        key = re.search(r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----", plain, re.S).group(0)
        key = "\n".join(line.strip() for line in key.splitlines()) + "\n"
        url = "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-" + version + ".zip"
        return validate(dict(version=version, url=url, sha256="", format="aws", member="aws/install",
                             signature_url=url + ".sig", public_key=key))
    raise ValueError("Unsupported binary tool: " + tool)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    parser.add_argument("version")
    parser.add_argument("--override", default="{}")
    parser.add_argument("--python-index", default="https://pypi.org/pypi")
    args = parser.parse_args()
    override = json.loads(args.override)
    if override:
        result = validate(override)
        if args.version not in ("latest", "lts") and result["version"] != args.version.removeprefix("v"):
            raise ValueError("Override version differs from requested version")
    else:
        result = resolve(args.tool, args.version, args.python_index)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, StopIteration, AttributeError, OSError) as error:
        print("Artifact resolution failed: " + str(error), file=sys.stderr)
        sys.exit(1)
