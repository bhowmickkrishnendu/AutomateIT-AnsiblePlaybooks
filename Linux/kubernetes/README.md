# Kubernetes Cluster Setup with Ansible

This playbook automates the setup of a Kubernetes cluster (v1.34) on Ubuntu-based systems using Ansible. It provisions both master and worker nodes, installs required dependencies, configures containerd, and sets up the Kubernetes repository using the new `pkgs.k8s.io` source.

## Inventory Example (`hosts.ini`)
```ini
[k8s-master]
192.168.40.150 ansible_user=root

[k8s-workers]
192.168.40.151 ansible_user=root
192.168.40.152 ansible_user=root

[all:vars]
ansible_python_interpreter=/usr/bin/python3
```

## Playbook Overview (`playbook.yml`)
- Updates apt cache and installs base dependencies
- Disables swap (required for Kubernetes)
- Loads required kernel modules and sysctl settings
- Installs and configures containerd as the container runtime
- Adds the Kubernetes apt repository (using `pkgs.k8s.io`)
- Installs `kubelet`, `kubeadm`, and `kubectl` (v1.34)
- Holds Kubernetes packages to prevent unintended upgrades

## Usage
1. **Edit your inventory:**
   - Update `hosts.ini` with your master and worker node IPs and SSH users.

2. **Run the playbook:**
   ```sh
   ansible-playbook -i hosts.ini playbook.yml
   ```

3. **Initialize the cluster (on master):**
   After running the playbook, SSH into your master node and run:
   ```sh
   sudo kubeadm init --apiserver-advertise-address=192.168.40.10 --pod-network-cidr=192.168.0.0/16
   ```
   Follow the output instructions to set up `kubectl` for your user and join worker nodes.

4. **Join worker nodes:**
   Run the `kubeadm join ...` command (from the `kubeadm init` output) on each worker node.

## Notes
- This playbook is designed for Ubuntu-based systems.
- It uses the latest Kubernetes v1.34 packages from the new `pkgs.k8s.io` repository.
- Swap is disabled and commented out in `/etc/fstab` as required by Kubernetes.
- Containerd is configured to use systemd cgroups.

## References
- [Kubernetes Official Docs](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/)
- [pkgs.k8s.io Migration Guide](https://kubernetes.io/blog/2023/08/15/pkgs-k8s-io-introduction/)

---
**Author:** Krishnendu Bhowmick
