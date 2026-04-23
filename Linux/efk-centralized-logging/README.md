# EFK Centralized Logging (Ansible)

This folder contains an Ansible playbook to set up an EFK stack:

- Elasticsearch
- Logstash
- Kibana

The playbook targets hosts in the `logservers` inventory group.

## Files in this folder

- `efk-centralized-logging.yaml`: Main playbook
- `elasticsearch.yml.j2`: Elasticsearch config template
- `kibana.yml.j2`: Kibana config template
- `logstash.yml.j2`: Logstash config template

## Prerequisites

1. Control machine with Ansible installed.
2. Managed hosts running a Debian/Ubuntu-based OS (the playbook uses `apt`).
3. SSH access to target hosts.
4. Inventory must contain a `logservers` group.
5. Add these systemd unit files (required by playbook tasks):
   - `logstash.service`
   - `elasticsearch.service`

   Place them where Ansible can copy them as referenced in the playbook.

## Required variables

The templates require these variables:

- `cluster_name`
- `elasticsearch_interface`
- `kibana_interface`
- `logstash_interface`

These variables should match interface suffixes from facts, for example `eth0` or `ens33`.

## Quick start

### 1) Create inventory

Example `inventory.ini`:

```ini
[logservers]
log01 ansible_host=192.168.1.10 ansible_user=ubuntu
log02 ansible_host=192.168.1.11 ansible_user=ubuntu
```

### 2) Create variable file

Example `group_vars/logservers.yml`:

```yaml
cluster_name: efk-cluster
elasticsearch_interface: ens33
kibana_interface: ens33
logstash_interface: ens33
```

### 3) Run the playbook

From this folder, run:

```bash
ansible-playbook -i inventory.ini efk-centralized-logging.yaml --become
```

## What the playbook does

1. Installs Java runtime (`openjdk-11-jre`).
2. Downloads and extracts Logstash under `/opt`.
3. Applies Logstash config and starts/enables `logstash` service.
4. Downloads and extracts Elasticsearch under `/opt`.
5. Applies Elasticsearch config and starts/enables `elasticsearch` service.
6. Downloads and installs Kibana `.deb` package.
7. Applies Kibana config and restarts `kibana` when changed.

## Validate deployment

Run on target host(s):

```bash
systemctl status elasticsearch
systemctl status logstash
systemctl status kibana
```

Check ports:

```bash
ss -tulnp | grep -E '9200|5601|5044'
```

Basic health checks:

```bash
curl http://<elasticsearch-host>:9200
curl http://<kibana-host>:5601
```

## Notes

- Version defaults in playbook:
  - Elasticsearch: `8.3.2`
  - Logstash: `8.3.2`
  - Kibana: `8.3.2`
- If your host does not expose Ansible facts for the selected interface name, update the interface variables accordingly.
- Ensure firewalls/security groups allow access to needed ports:
  - 9200 (Elasticsearch)
  - 5601 (Kibana)
  - 5044 (Logstash Beats input)

## Troubleshooting

- If template rendering fails, verify interface variable names and inventory group membership.
- If services fail to start, inspect logs:

```bash
journalctl -u elasticsearch -xe
journalctl -u logstash -xe
journalctl -u kibana -xe
```

- If the playbook fails on service file copy steps, confirm `logstash.service` and `elasticsearch.service` are available in your Ansible project path.
