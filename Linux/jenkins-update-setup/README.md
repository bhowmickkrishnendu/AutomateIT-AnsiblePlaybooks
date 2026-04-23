# Jenkins Update Through Ansible

An Ansible playbook to update Jenkins by downloading a specific Jenkins WAR file, stopping Jenkins, replacing existing `jenkins.war` files, and starting Jenkins again.

## File in this folder

- `jenkins-update-through-ansible.yaml`

## What this playbook does

The playbook runs these steps on your target host(s):

1. Finds all current `jenkins.war` file locations.
2. Downloads Jenkins WAR version **2.440.1** to `/tmp/jenkins.war`.
3. Stops the Jenkins service.
4. Transfers/synchronizes the WAR file via the `synchronize` task.
5. Copies the new WAR file to all discovered Jenkins WAR locations.
6. Starts the Jenkins service.

## Prerequisites

Before running:

- Ansible installed on your control machine.
- SSH access to target Linux server(s).
- A valid Ansible inventory.
- Sudo privileges on target machine(s) (playbook uses `become: yes`).
- Jenkins service name is `jenkins` on target host.
- Internet access from target host for download URL:
  - `https://updates.jenkins.io/download/war/2.440.1/jenkins.war`

## Quick start

### 1) Create or use an inventory

Example inventory file (`inventory.ini`):

```ini
[jenkins]
192.168.1.20 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### 2) (Recommended) Verify connectivity

```bash
ansible -i inventory.ini all -m ping
```

### 3) Run in check mode first (dry run)

```bash
ansible-playbook -i inventory.ini jenkins-update-through-ansible.yaml --check
```

### 4) Run the playbook

```bash
ansible-playbook -i inventory.ini jenkins-update-through-ansible.yaml
```

## How to change Jenkins version

The Jenkins version is hardcoded in the playbook URL.

Current value:

- `https://updates.jenkins.io/download/war/2.440.1/jenkins.war`

To update to another version, edit the URL in `jenkins-update-through-ansible.yaml`.

## Verify update after run

On the target server:

```bash
systemctl status jenkins
```

Then open Jenkins in browser and confirm the version from:

- Manage Jenkins -> System Information

## Troubleshooting

### Jenkins service fails to start

- Check logs:

```bash
sudo journalctl -u jenkins -n 100 --no-pager
```

- Confirm Java/Jenkins compatibility.

### `synchronize` task issues

The playbook includes a `synchronize` task that may require `rsync` setup.
If this task fails in your environment, ensure `rsync` is installed and reachable where needed.

### No `jenkins.war` paths found

If no existing WAR file is found, the copy loop step is skipped. Confirm Jenkins installation path and permissions.

## Notes

- This playbook updates existing `jenkins.war` locations discovered at runtime.
- Always test in non-production first.
- Consider backing up Jenkins home and WAR before production updates.
