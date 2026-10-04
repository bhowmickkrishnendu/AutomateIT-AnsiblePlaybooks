# Selectable DevOps tools for Linux

An Ansible role and two entrypoints for provisioning x86-64 Linux workstations or
remote hosts. Every tool is optional; the role defaults to an empty selection.
VS Code profiles and extensions are configured manually after installation.

## Quick start

Run from a Linux control node with Python 3.12+, Ansible Core 2.20+, SSH access
(for remote targets), and permission to use sudo. Installing Ansible on a target
does not provide the Ansible control node needed to start this playbook.

```bash
cd Linux/devops-tools
cp inventory.example.ini inventory.ini
# Edit inventory.ini to select the intended hosts.
ansible-playbook -i inventory.ini interactive.yml --ask-become-pass
```

The interactive entrypoint asks for tools and permission to upgrade existing
tools. It asks for Python, Node.js, Go versions and the Docker group user only
when those tools are selected. Press Enter to accept the displayed default.
Selections apply to all hosts in the `devops` inventory group. Use separate
inventory groups/runs if hosts need different interactive choices.

For unattended installation:

```bash
cp config.example.yml config.yml
# Edit config.yml: remove unwanted tools; select versions and Docker user.
ansible-playbook -i inventory.ini playbook.yml -e @config.yml --ask-become-pass
```

For a smaller selection, without copying a configuration file:

```bash
ansible-playbook -i inventory.ini playbook.yml \
  -e '{"devops_selected_tools":["git","jq","kubectl"]}' --ask-become-pass
```

Put host-specific settings in inventory host/group variables. Do not commit
passwords, credentials, tokens, or proxy passwords. Inventory examples contain
no real hosts. `--limit` can restrict any run to a subset of inventory hosts.

## Operating systems

The explicit implementation allowlist is Ubuntu 22.04/24.04/26.04,
Fedora 43/44, RHEL 9/10, and Rocky Linux 9/10 on x86-64. Other releases fail
preflight. This is an implementation target matrix, **not a certification that
each release has passed installation tests**. Linux integration runs remain
required before enterprise rollout. Maintain the allowlist with your OS lifecycle
policy; distribution support alone does not guarantee availability of every tool.

RHEL needs active access to its configured package repositories. Rocky uses
Docker's CentOS repository; verify package compatibility on your target release.
Upstream GPG keys can conflict with newer/FIPS crypto policies; the playbook fails
verification rather than weakening the host's policy. Docker requires systemd.

Python 3 is bootstrapped only when missing. Check mode cannot bootstrap Python;
a Python-less host must first receive Python through a normal run or approved
image/bootstrap process. Bootstrap package transactions are the only raw shell
tasks; other installation tasks use Ansible modules or argument-vector commands.

## Tools and version selection

| Configuration name | Installation method | Version policy |
| --- | --- | --- |
| `awscli` | Official AWS CLI v2 zip with PGP verification | `latest` or exact v2 version |
| `kubectl` | Official binary with upstream SHA256 | `latest` or exact version |
| `helm` | Official archive with upstream SHA256 | `latest` or exact version |
| `terraform` | Official HashiCorp archive with SHA256 | `latest` or exact version |
| `nodejs` | Official Node.js archive with SHA256 | `lts`, `latest`, or exact version |
| `go` | Official Go archive with SHA256 | `latest` or exact version |
| `yq` | Mike Farah release binary with GitHub SHA256 | `latest` or exact version |
| `trivy` | Official release archive with SHA256 | `latest` or exact version |
| `github_cli` | Official release archive with SHA256 | `latest` or exact version |
| `shellcheck` | Official release archive with GitHub SHA256 | `latest` or exact version |
| `ansible` | Full Ansible package in a dedicated virtual environment | `latest` or exact package version |
| `ansible_lint` | Dedicated virtual environment | `latest` or exact package version |
| `pipx` | Dedicated virtual environment | `latest` or exact version |
| `python` | Configured distribution repositories | `system` or additional `3.x` interpreter |
| `git`, `jq` | Distribution packages | Present; latest distribution package when upgrades enabled |
| `vscode` | Official signed Microsoft repository | Present; latest when upgrades enabled |
| `docker` | Official signed Docker repository, including Compose/Buildx | Present; latest when upgrades enabled |

Exact versions use `major.minor.patch`, optionally prefixed by `v`. Additional
Python uses `major.minor`, for example `3.12`, and receives the patch release
available in your configured OS repositories. Unsupported Python package choices
fail; this role does not compile Python or enable third-party repositories.
The additional interpreter never replaces `/usr/bin/python3` or the interpreter
used by Ansible to manage the OS.

Latest Ansible/lint packages can require a newer Python than the OS default.
Select an available additional Python and include `python` in the tool list, or
set `devops_python_executable` to an approved existing interpreter. Additional
Python is processed first and automatically used for managed Python tooling.
For example, on Ubuntu 24.04:

```yaml
devops_selected_tools: [python, ansible, ansible_lint, pipx]
devops_versions:
  python: '3.12'
  ansible: latest
  ansible_lint: latest
```

`latest` Python packages resolve to the actual latest published package version;
installation fails on an incompatible interpreter rather than silently installing
an older release. Configure a compatible runtime or pin a compatible package.
The Ansible package version differs from the `ansible-core` version printed by
`ansible --version`.

For kubectl, ensure the selected version meets the Kubernetes
[client version-skew policy](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/).
Latest Helm can move to a new major version; pin it when compatibility matters.

## Existing installations and idempotency

* `devops_upgrade_existing: false` preserves an existing working tool when its
  policy is `latest`, `lts`, or `system`. Latest is used for **new installations**.
* An exact version explicitly requests version reconciliation, including a
  downgrade, for installations owned by this role. Additional Python is installed
  alongside the system interpreter.
* `devops_upgrade_existing: true` permits checking upstream releases and updating
  selected tools. Distribution packages use their configured repository versions.
* Disabling/deselecting a tool does not uninstall it or remove its repositories.
* External binary/Python installations are preserved by default. An explicitly
  requested change fails with guidance if it would take over an external
  installation; remove that installation deliberately before transferring
  ownership. The role does not automatically uninstall distro/snap/user installs.
* Installations are root-owned under `/opt/devops-tools`; executable links are
  created under `/usr/local/bin`. Earlier managed binary versions are retained.
* Version checks, metadata reads, and fact collection report no change. Pinned
  binaries with matching versions skip download/extraction/installer work.

Given unchanged upstream releases and host state, a second normal run should
report `changed=0`. A stale apt cache refresh, a newly published release during an
upgrade-enabled run, or an external host change can legitimately change the recap.
The current implementation does not provide transactional rollback or uninstall.

## Docker and Podman

When a `podman` executable is already present in the privileged installation PATH,
Docker installation, service changes, and Docker group changes are skipped.
Podman is not installed by this role. A Podman compatibility `docker` command is
also left untouched when Podman is detected.

When Docker is selected and Podman is absent, the role enables/starts Docker and
adds an existing user to its group, even if Docker's current version is preserved.
The interactive prompt accepts a username; its empty default resolves to the
inventory SSH user or local `SUDO_USER`/`USER`. Root and nonexistent users fail
preflight; for root-based automation set `devops_docker_user` explicitly.
Membership grants root-equivalent access and takes effect after a new login.

## Verification, security, and errors

TLS verification is enabled. Binary downloads require SHA256 values obtained
from official HTTPS metadata or GitHub's release-asset digest. SHA256 detects
artifact corruption but shares trust with the upstream HTTPS metadata; it is not
an independent publisher signature. AWS CLI additionally requires a valid PGP
signature from its pinned official key. Apt keys are scoped with `signed-by`;
RPM repositories require package signatures. Key rotation fails closed and needs
a reviewed fingerprint update.

Every selected working tool receives a local version check; binary installations
also assert the resolved exact version. Cloud logins, Kubernetes connectivity,
Trivy database downloads/scans, Docker workloads, and VS Code GUI startup are
outside installation verification. No AWS/Kubernetes/GitHub credentials are set.

Network/package operations have bounded timeouts and retry transient errors
(such as connection failures, rate limiting, or package-manager locks).
Permanent failures, including missing versions and invalid checksums, stop immediately. An unrecoverable
task ends provisioning for that host, prints completed tool statuses plus the
failure, and leaves the Ansible recap failed. Other inventory hosts continue.
Fix the cause and rerun; completed installations are retained. The summary
distinguishes preserved, installed, reconciled, Podman-skipped, and planned tools;
`reconciled` does not necessarily mean changed (the recap is authoritative).

## Proxies and mirrors

`devops_environment` is passed to managed-host operations, including Python
metadata requests, Ansible downloads, and pip. Use `https_proxy`, `http_proxy`,
`no_proxy`, and an approved system CA for corporate TLS interception. Do not
disable certificate verification. Install OS package mirrors through your normal
host baseline; the role preserves those repositories and adds official Docker/
VS Code repositories only when those tools need management.

For signed Docker/VS Code package mirrors, set `devops_repository_overrides`:

```yaml
devops_repository_overrides:
  docker:
    key_url: https://packages.example.com/keys/docker.asc
    # Set an independently approved signing-key fingerprint (40 uppercase hex).
    fingerprint: 9DC858229FC7DD38854AE2D88D81803C0EBFCD88
    apt_url: https://packages.example.com/docker/ubuntu
    apt_suite: noble
    apt_component: stable
    # RPM hosts can instead override rpm_baseurl and the RPM key fingerprint.
```

Overrides apply only to selected repository tools. HTTPS, scoped apt keys, and
signature checks remain mandatory. Preserve upstream signatures where possible;
review a new fingerprint when your mirror re-signs packages.

For Python package mirrors, use `devops_pip_extra_args` or `PIP_INDEX_URL` in
`devops_environment`. Latest resolution uses `devops_pypi_metadata_base`
(default `https://pypi.org/pypi`); change it to an internal PyPI-compatible JSON API
or pin versions to avoid that metadata request. Pip enforces wheel/source metadata
compatibility; dependencies are not locked or hash-pinned. Environments requiring
fully reproducible Python supply chains should use an approved locked mirror.

Binary mirrors provide complete `devops_artifact_overrides` descriptors:

```yaml
devops_versions:
  kubectl: '1.35.1'
devops_artifact_overrides:
  kubectl:
    version: '1.35.1'
    url: https://artifacts.example.com/kubectl/1.35.1/linux/amd64/kubectl
    sha256: REPLACE_WITH_APPROVED_64_CHARACTER_SHA256
    format: raw
    member: kubectl
```

Allowed formats: `raw`, `tar`, `zip`, `aws`. For archives, `member` is the
relative executable path inside the archive. Archive overrides must preserve the
official layout (especially Node.js/Go/AWS). AWS overrides additionally require
`signature_url` and the official `public_key`; the pinned AWS signer still applies.
Checksums cannot be omitted and HTTP URLs are rejected. Only use trusted archives.

## Dry run and validation

```bash
ansible-playbook -i inventory.ini playbook.yml -e @config.yml --check --diff
```

Dry run gathers facts, validates configuration/user/runtime, inspects existing
tools, and prints planned tools. It does not contact release APIs or download,
install, create environments, add repositories, or change Docker access. It is a
planning mode, not a complete package transaction simulation; it cannot predict
repository availability, exact latest versions, installer failures, or reboot needs.
An absent Python interpreter prevents dry-run fact gathering. No automatic reboot
or blanket operating-system upgrade is performed by this playbook.

On a Linux development/control node:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
source .venv/bin/activate
python -m unittest discover -s tests -v
yamllint .
ansible-playbook -i inventory.example.ini playbook.yml --syntax-check
ansible-playbook -i inventory.example.ini interactive.yml --syntax-check
ansible-lint -c .ansible-lint playbook.yml interactive.yml
```

Offline tests cover metadata formats, integrity failures, version matching,
installation policy, YAML/Jinja parsing, and task/catalog consistency. They do not
substitute for Linux installation tests. Validate each release/tool combination
on a disposable VM before broader deployment, including Docker/systemd and GUI
package prerequisites. To assert a second run has no changes:

```bash
bash tests/integration.sh -i inventory.test.ini -e @config.test.yml --ask-become-pass
for run
ansible-playbook -i inventory.example.ini interactive.yml -K
```

This script performs real installations twice against the supplied inventory.
Use disposable hosts, pinned versions where possible, and a recently warmed
package cache. Check the supported matrix, preservation/conflict cases, Podman
skipping, Docker membership, fresh installs, explicit upgrades/downgrades, failure
reporting, and check mode. Installation and repeat-run validation were not executed
in the Windows authoring workspace because Linux execution was unavailable.

Official installation references: [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
[kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/),
[Helm](https://helm.sh/docs/intro/install/),
[Docker](https://docs.docker.com/engine/install/),
[VS Code](https://code.visualstudio.com/docs/setup/linux),
[GitHub CLI](https://github.com/cli/cli/blob/trunk/docs/install_linux.md).
