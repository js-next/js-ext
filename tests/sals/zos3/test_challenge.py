from io import StringIO

from jumpscale.sals.zos3.workload import Workload
from jumpscale.sals.zos3.workload.container import Container, Mount, Member, Capacity
from jumpscale.sals.zos3.workload.ipv4 import PublicIP
from jumpscale.sals.zos3.workload.kubernates import Kubernetes
from jumpscale.sals.zos3.workload.network import Peer, Network
from jumpscale.sals.zos3.workload.volume import Volume
from jumpscale.sals.zos3.workload.zdb import ZDB


def test01_network():
    peer = Peer(subnet="10.100.0.0", wireguard_public_key="aa", allowed_ips=["10.100.0.1"])
    net = Network(
        name="test",
        ip_range="10.100.0.0/16",
        subnet="10.100.0.0/16",
        wireguard_private_key_encrypted="xx",
        wireguard_listen_port=5522,
        peers=[peer],
        endpoint="",
    )

    w = Workload(user_id="test1")
    w.data = net
    print(w.to_dict())
    print(w.signature)


def test02_kubernetes():
    k8s = Kubernetes(
        size=1,
        cluster_secret=1,
        network_id="aaaaaaa",
        ip="10.100.0.1",
        master_ips=["10.100.0.3"],
        ssk_keys=["aaaa"],
        public_ip="62.184.101.100",
    )
    w = Workload(user_id="test2")
    w.data = k8s
    print(w.to_dict())
    print(w.signature)


def test03_container():
    mounts = [Mount(volume_id="dev1", mountpoint="/mnt")]
    network = Member(network_id="aaa", ips=["10.0.0.1"], public_ip6=True, yggdrasil_ip=True)
    capacity = Capacity(cpu=1, memory=1, disk_type="ssd", disk_size=1)

    cont = Container(
        flist="https://files.list",
        hub_url="http://hub.grid.tf",
        entrypoint="/bin/bash",
        env={},
        secret_env={},
        mounts=mounts,
        network=network,
        capacity=capacity,
    )

    w = Workload(user_id="test3")
    w.data = cont
    print(w.to_dict())
    print(w.signature)


def test04_ipv4():
    ip = PublicIP(ip="62.184.101.100")

    w = Workload(user_id="test4")
    w.data = ip
    print(w.to_dict())
    print(w.signature)


def test05_volume():
    v = Volume(size=1, type="ssd")

    w = Workload(user_id="test5")
    w.data = v
    print(w.to_dict())
    print(w.signature)


def test06_zdb():
    z = ZDB(size=1, mode="seq", password_encrypted="aaaaaa", disk_type="ssd", public=True)

    w = Workload(user_id="test6")
    w.data = z
    print(w.to_dict())
    print(w.signature)
