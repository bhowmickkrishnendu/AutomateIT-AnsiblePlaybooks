# AutomateIT-AnsiblePlaybooks

A curated collection of Ansible playbooks and templates for automating IT operations on both Linux and Windows systems. This repository is designed to help system administrators and DevOps engineers quickly deploy, configure, and manage infrastructure components.

## Repository Structure

```
AutomateIT-AnsiblePlaybooks/
├── LICENSE
├── README.md
├── Linux/
│   ├── deploy_tomcat_service.yml
│   ├── efk-centralized-logging.yml
│   ├── elasticsearch.yml.j2
│   ├── firewall-configuration-deny-all-allow-rule.yml
│   ├── jenkins-update-through-ansible.yaml
│   ├── kibana.yml.j2
│   ├── logstash.yml.j2
│   ├── monitoring-stack-setup-readme.txt
│   ├── monitoring-stack-setup.yml
│   ├── node_exporter_setup.yml
│   ├── openjdk-11-jdk-installler.yml
│   ├── package-updates-redhat-systems.yml
│   ├── package-updates-ubuntu-baseed.yml
│   ├── password-update-user-specific.yml
│   ├── sonarqube-install.yml
│   ├── tomcat_setup.yml
│   ├── tomcat.service.j2
│   ├── user-management-deactivation.yml
│   ├── user-management-retrive-current-users.yml
│   ├── user-management-with-sudo.yml
│   ├── user-management-without-sudo.yml
│   ├── webserver-setup.yml
│   └── kubernetes/
│       ├── hosts.ini
│       ├── playbook.yml
│       └── README.md
└── Windows/
        ├── configure_firewall.yaml
        ├── copy_from_host_to_another_host.yaml
        ├── copy_paste.yaml
        ├── deploy_iis.yaml
        ├── fetch_public_ip.ps1
        ├── get_public_ip.yaml
        ├── install_software.yaml
        ├── manage_services.yaml
        ├── manage_tasks.yaml
        ├── manage_users_groups.yaml
        ├── monitor_system_performance.yaml
        └── update_windows.yaml
```

## Linux Playbooks
- **Application Deployment:**
    - `deploy_tomcat_service.yml`, `tomcat_setup.yml`, `openjdk-11-jdk-installler.yml`
- **Monitoring & Logging:**
    - `efk-centralized-logging.yml`, `monitoring-stack-setup.yml`, `node_exporter_setup.yml`, `elasticsearch.yml.j2`, `kibana.yml.j2`, `logstash.yml.j2`
- **User & System Management:**
    - `user-management-*.yml`, `password-update-user-specific.yml`, `package-updates-redhat-systems.yml`, `package-updates-ubuntu-baseed.yml`, `firewall-configuration-deny-all-allow-rule.yml`
- **CI/CD & Tools:**
    - `jenkins-update-through-ansible.yaml`, `sonarqube-install.yml`
- **Kubernetes:**
    - `kubernetes/playbook.yml`, `kubernetes/hosts.ini`

## Windows Playbooks
- **System & User Management:**
    - `configure_firewall.yaml`, `manage_users_groups.yaml`, `manage_services.yaml`, `manage_tasks.yaml`, `update_windows.yaml`
- **Deployment & Utilities:**
    - `deploy_iis.yaml`, `install_software.yaml`, `copy_from_host_to_another_host.yaml`, `copy_paste.yaml`, `fetch_public_ip.ps1`, `get_public_ip.yaml`, `monitor_system_performance.yaml`

## Usage
1. **Clone the repository:**
     ```sh
     git clone https://github.com/bhowmickkrishnendu/AutomateIT-AnsiblePlaybooks.git
     cd AutomateIT-AnsiblePlaybooks
     ```
2. **Customize inventory and variables** as needed for your environment.
3. **Run a playbook:**
     ```sh
     ansible-playbook -i <inventory_file> <playbook.yml>
     ```

## Contributing
Contributions are welcome! Please open issues or submit pull requests for improvements or new playbooks.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
