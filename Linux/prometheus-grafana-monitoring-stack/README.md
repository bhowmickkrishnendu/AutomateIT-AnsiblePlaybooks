# Prometheus + Grafana Monitoring Stack (Ansible)

This folder contains two Ansible playbooks:

- `monitoring-stack-setup.yaml`: installs and configures Prometheus, Grafana, and Node Exporter on a monitoring server.
- `node_exporter_setup.yaml`: installs and configures Node Exporter on client systems.

## What this setup gives you

- Prometheus running on port `9090`
- Grafana running on port `3000`
- Node Exporter running on port `9100`
- Systemd services enabled and started for all components

## Prerequisites

- Control machine with Ansible installed
- SSH access to target Linux hosts
- Sudo privileges on target hosts (`become: true` is used)
- Debian/Ubuntu-based targets (playbooks use `apt`)

## Recommended inventory

Create an inventory file, for example `inventory.ini`:

```ini
[monitoring]
monitor1 ansible_host=10.10.10.10 ansible_user=ubuntu

[client_systems]
app1 ansible_host=10.10.10.21 ansible_user=ubuntu
app2 ansible_host=10.10.10.22 ansible_user=ubuntu
```

## Run the playbooks

Run from this folder:

```bash
ansible-playbook -i inventory.ini monitoring-stack-setup.yaml
ansible-playbook -i inventory.ini node_exporter_setup.yaml
```

## Access URLs

After successful run:

- Prometheus: `http://<monitoring-host>:9090`
- Grafana: `http://<monitoring-host>:3000`

Grafana default credentials are typically:

- Username: `admin`
- Password: `admin`

Grafana forces password change at first login.

## Verify services on target hosts

On monitoring host:

```bash
sudo systemctl status prometheus grafana-server node_exporter
sudo ss -tulnp | grep -E '9090|3000|9100'
```

On client hosts:

```bash
sudo systemctl status node_exporter
sudo ss -tulnp | grep 9100
```

## Add client systems to Prometheus

The `monitoring-stack-setup.yaml` playbook configures Prometheus with localhost Node Exporter by default.
To scrape remote clients, update `/etc/prometheus/prometheus.yml` on the monitoring host and add targets under `node_exporter`:

```yaml
- job_name: node_exporter
  static_configs:
    - targets:
      - localhost:9100
      - 10.10.10.21:9100
      - 10.10.10.22:9100
```

Then reload/restart Prometheus:

```bash
sudo systemctl restart prometheus
```

## Common issues and quick fixes

- Port blocked by firewall: allow `3000`, `9090`, and `9100` as needed.
- SSH/auth issues: test with `ansible all -i inventory.ini -m ping`.
- DNS/host mismatch: use `ansible_host` in inventory.
- Package download failures: verify outbound internet from target hosts.

## Notes

- Versions are defined in playbook vars and can be changed safely.
- Playbooks are idempotent for repeated runs.
