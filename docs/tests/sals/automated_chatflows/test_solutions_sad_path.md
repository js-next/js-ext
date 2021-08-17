### test01_ubuntu_with_specific_node

Test case for deploying Ubuntu with specific node.

**Test Scenario**

- Deploy Ubuntu.
- Check that Ubuntu is reachable.

### test02_kubernetes_with_different_sizes_0_kub_size

Test case for Deploying a kubernetes with different size [with _='kub_size', kub_size='vCPU: 2, RAM: 5 GiB, Disk Space: 50 GiB'].

**Test Scenario**

- Deploy kubernetes.
- Check that kubernetes is reachable.

### test02_kubernetes_with_different_sizes_1_kub_size

Test case for Deploying a kubernetes with different size [with _='kub_size', kub_size='vCPU: 4, RAM: 16 GiB, Disk Space: 400 GiB'].

**Test Scenario**

- Deploy kubernetes.
- Check that kubernetes is reachable.

### test02_kubernetes_with_different_sizes_2_kub_size

Test case for Deploying a kubernetes with different size [with _='kub_size', kub_size='vCPU: 8, RAM: 32 GiB, Disk Space: 100 GiB'].

**Test Scenario**

- Deploy kubernetes.
- Check that kubernetes is reachable.

### test03_minio_with_with_master_slave

Test case for deploying Minio with master/slave.

**Test Scenario**

- Deploy Minio with master/slave.
- Check that Minio is reachable.

### test04_network_add_access

Test case for adding access for network.

**Test Scenario**

- Deploy network.
- Add access to this network.
- Up wireguard.
- Check that network is reachable.

### test05_deploy_network_with_ipv6

Test case for deploying a network with IPv6.

**Test Scenario**

- Deploy a 4to6 GW.
- Get and up GW wireguard.
- Deploy network with IPv6.
- Up network wireguard.
- Check that network is reachable.

### test06_network_with_specific_ip

Test case for deploying a network with specific IP.

**Test Scenario**

- Deploy Nwtwork with specific IP.
- Up wireguard.
- Check that Network is reachable.

### test07_generic_flist_with_nonexist_flist

Test case for deploying a container with a generic flist.

**Test Scenario**

- Deploy a container with a none exist flist.
- Check that generic flist deploying has been failed.
