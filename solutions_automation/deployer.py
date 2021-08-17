from solutions_automation.dashboard_solutions.delegated_domain import DomainDelegationAutomated
from solutions_automation.dashboard_solutions.exposed import SolutionExposeDeployAutomated
from solutions_automation.dashboard_solutions.generic_flist import FlistAutomated
from solutions_automation.dashboard_solutions.kubernetes import KubernetesAutomated
from solutions_automation.dashboard_solutions.minio import MinioAutomated
from solutions_automation.dashboard_solutions.monitoring import MonitoringAutomated
from solutions_automation.dashboard_solutions.network import NetworkDeployAutomated
from solutions_automation.dashboard_solutions.network_access import NetworkAccessAutomated
from solutions_automation.dashboard_solutions.pools import PoolAutomated
from solutions_automation.dashboard_solutions.extend_pools import PoolExtendAutomated
from solutions_automation.dashboard_solutions.four_to6gw import FourToSixGatewayAutomated
from solutions_automation.dashboard_solutions.etcd import EtcdAutomated
from solutions_automation.dashboard_solutions.ubuntu import UbuntuAutomated
from solutions_automation.marketplace.blog import BlogAutomated
from solutions_automation.marketplace.cryptpad import CryptpadAutomated
from solutions_automation.marketplace.discourse import DiscourseAutomated
from solutions_automation.marketplace.gitea import GiteaAutomated
from solutions_automation.marketplace.mattermost import MattermostAutomated
from solutions_automation.marketplace.meetings import MeetingsAutomated
from solutions_automation.marketplace.peertube import PeertubeAutomated
from solutions_automation.marketplace.taiga import TaigaAutomated
from solutions_automation.marketplace.website import WebsiteAutomated
from solutions_automation.marketplace.wiki import WikiAutomated
from solutions_automation.threebot.deploy import ThreebotDeployAutomated
from solutions_automation.threebot.change_size import ThreebotChangeSizeAutomated
from solutions_automation.threebot.start import ThreebotStart
from solutions_automation.threebot.change_location import ThreebotChangeLocation


def deploy_gitea(solution_name, wg_config="NO", debug=True):
    return GiteaAutomated(solution_name=solution_name, wg_config=wg_config, debug=debug)


def deploy_cryptpad(solution_name, flavor="Silver", wg_config="NO", debug=True):
    return CryptpadAutomated(solution_name=solution_name, flavor=flavor, wg_config=wg_config, debug=debug)


def deploy_mattermost(solution_name, flavor="Silver", wg_config="NO", debug=True):
    return MattermostAutomated(solution_name=solution_name, flavor=flavor, wg_config=wg_config, debug=debug)


def deploy_meetings(solution_name, flavor="Silver", wg_config="NO", debug=True):
    return MeetingsAutomated(solution_name=solution_name, flavor=flavor, wg_config=wg_config, debug=debug)


def deploy_wiki(solution_name, title, repo, branch, wg_config="NO", debug=True):
    return WikiAutomated(
        solution_name=solution_name, title=title, repo=repo, branch=branch, wg_config=wg_config, debug=debug
    )


def deploy_website(solution_name, title, repo, branch, wg_config="NO", debug=True):
    return WebsiteAutomated(
        solution_name=solution_name, title=title, repo=repo, branch=branch, wg_config=wg_config, debug=debug
    )


def deploy_blog(solution_name, title, repo, branch, wg_config="NO", debug=True):
    return BlogAutomated(
        solution_name=solution_name, title=title, repo=repo, branch=branch, wg_config=wg_config, debug=debug
    )


def deploy_discourse(solution_name, host_email, smtp_host, host_email_password, wg_config="NO", debug=True):
    return DiscourseAutomated(
        solution_name=solution_name,
        host_email=host_email,
        smtp_host=smtp_host,
        host_email_password=host_email_password,
        wg_config=wg_config,
        debug=debug,
    )


def deploy_peertube(solution_name, flavor="Silver", wg_config="NO", debug=True):
    return PeertubeAutomated(solution_name=solution_name, flavor=flavor, wg_config=wg_config, debug=debug)


def deploy_taiga(solution_name, host_email, smtp_host, host_email_password, secret, wg_config="NO", debug=True):
    return TaigaAutomated(
        solution_name=solution_name,
        host_email=host_email,
        smtp_host=smtp_host,
        host_email_password=host_email_password,
        secret=secret,
        wg_config=wg_config,
        debug=debug,
    )


def deploy_ubuntu(
    solution_name,
    pool="choose_random",
    version="ubuntu-18.04",
    cpu=1,
    memory=1024,
    disk_size=256,
    disk_type="SSD",
    log="NO",
    ssh="~/.ssh/id_rsa.pub",
    ipv6="NO",
    node_automatic="YES",
    node="choose_random",
    ipv4="choose_random",
    network="choose_random",
    debug=True,
):
    return UbuntuAutomated(
        solution_name=solution_name,
        pool=pool,
        version=version,
        cpu=cpu,
        memory=memory,
        disk_size=disk_size,
        disk_type=disk_type,
        log=log,
        ssh=ssh,
        ipv6=ipv6,
        node_automatic=node_automatic,
        node=node,
        ipv4=ipv4,
        network=network,
        debug=debug,
    )


def deploy_kubernetes(
    solution_name,
    secret,
    size="vCPU: 1, RAM: 2 GiB, Disk Space: 25 GiB",
    workernodes=1,
    network="choose_random",
    public_ip="No",
    pools="multi_choice",
    ssh="~/.ssh/id_rsa.pub",
    debug=True,
):
    return KubernetesAutomated(
        solution_name=solution_name,
        secret=secret,
        size=size,
        workernodes=workernodes,
        network=network,
        public_ip=public_ip,
        pools=pools,
        ssh=ssh,
        debug=debug,
    )


def deploy_minio(
    solution_name,
    username,
    password,
    setup="single",
    zdb_disk_type="HDD",
    zdb_size=10,
    cpu=1,
    memory=1024,
    data_shards=2,
    parity_shards=1,
    network="choose_random",
    ipv4="choose_random",
    ipv6="NO",
    container_pool="choose_random",
    zdb_pools="multi_choice",
    log="NO",
    ssh="~/.ssh/id_rsa.pub",
    node_automatic="YES",
    node="choose_random",
    debug=True,
):

    return MinioAutomated(
        solution_name=solution_name,
        username=username,
        password=password,
        setup=setup,
        zdb_disk_type=zdb_disk_type,
        zdb_size=zdb_size,
        cpu=cpu,
        memory=memory,
        data_shards=data_shards,
        parity_shards=parity_shards,
        network=network,
        ipv4=ipv4,
        container_pool=container_pool,
        zdb_pools=zdb_pools,
        log=log,
        ssh=ssh,
        ipv6=ipv6,
        node_automatic=node_automatic,
        node=node,
        debug=debug,
    )


def deploy_4to6gw(public_key="", gateway="choose_random", debug=True):
    return FourToSixGatewayAutomated(public_key=public_key, gateway=gateway, debug=debug)


def deploy_etcd(
    solution_name,
    network="choose_random",
    etcd_nodes=1,
    cpu=1,
    memory=1024,
    disk_size=1024,
    pool="choose_random",
    ipv6="NO",
    node_automatic="YES",
    address_etcd_node="choose_random",
):
    return EtcdAutomated(
        solution_name=solution_name,
        network=network,
        etcd_nodes=etcd_nodes,
        cpu=cpu,
        memory=memory,
        disk_size=disk_size,
        pool=pool,
        ipv6=ipv6,
        node_automatic=node_automatic,
        address_etcd_node=address_etcd_node,
    )


def delegated_domain(domain, gateway="choose_random", debug=True):
    return DomainDelegationAutomated(domain=domain, gateway=gateway, debug=debug)


def deploy_generic_flist(
    solution_name,
    flist,
    cpu=1,
    memory=1024,
    disk_size=256,
    vol="NO",
    corex="YES",
    entry_point="",
    env_vars={"name": "TEST"},
    log="NO",
    redis_chaneel_type="redis",
    redis_ip="",
    redis_port="",
    redis_channel_name="",
    ipv6="NO",
    node_automatic="YES",
    node="choose_random",
    ipv4="choose_random",
    network="choose_random",
    pool="choose_random",
    debug=True,
):
    return FlistAutomated(
        solution_name=solution_name,
        flist=flist,
        cpu=cpu,
        memory=memory,
        disk_size=disk_size,
        vol=vol,
        corex=corex,
        entry_point=entry_point,
        env_vars=env_vars,
        log=log,
        redis_chaneel_type=redis_chaneel_type,
        redis_ip=redis_ip,
        redis_port=redis_port,
        redis_channel_name=redis_channel_name,
        ipv6=ipv6,
        node_automatic=node_automatic,
        node=node,
        ipv4=ipv4,
        network=network,
        pool=pool,
        debug=debug,
    )


def deploy_monitoring(
    solution_name,
    ssh="~/.ssh/id_rsa.pub",
    cpu=1,
    memory=1024,
    disk_size=256,
    volume_size=10,
    network="choose_random",
    redis_node_select="YES",
    redis_pool="choose_random",
    redis_ip="choose_random",
    redis_node="choose_random",
    prometheus_node_select="YES",
    prometheus_pool="choose_random",
    prometheus_ip="choose_random",
    prometheus_node="choose_random",
    grafana_node_select="YES",
    grafana_pool="choose_random",
    grafana_ip="choose_random",
    grafana_node="choose_random",
    debug=True,
):
    return MonitoringAutomated(
        solution_name=solution_name,
        ssh=ssh,
        cpu=cpu,
        memory=memory,
        disk_size=disk_size,
        volume_size=volume_size,
        network=network,
        redis_node_select=redis_node_select,
        redis_pool=redis_pool,
        redis_ip=redis_ip,
        redis_node=redis_node,
        prometheus_node_select=prometheus_node_select,
        prometheus_pool=prometheus_pool,
        prometheus_ip=prometheus_ip,
        prometheus_node=prometheus_node,
        grafana_node_select=grafana_node_select,
        grafana_pool=grafana_pool,
        grafana_ip=grafana_ip,
        grafana_node=grafana_node,
        debug=True,
    )


def create_network(
    solution_name,
    pool="choose_random",
    ip_version="IPv4",
    ip_select="Choose ip range for me",
    ip_range="",
    access_node="choose_random",
    debug=True,
):
    return NetworkDeployAutomated(
        solution_name=solution_name,
        pool=pool,
        type="Create",
        ip_version=ip_version,
        ip_select=ip_select,
        ip_range=ip_range,
        access_node=access_node,
        debug=True,
    )


def add_access_to_network(
    network_name, ip_version="IPv4", access_node="choose_random", pool="choose_random", debug=True
):
    return NetworkAccessAutomated(
        network_name=network_name, ip_version=ip_version, access_node=access_node, pool=pool, debug=True
    )


def deploy_exposed(
    type,
    solution_to_expose,
    sub_domain,
    domain="choose_random",
    tls_port=6443,
    port=6443,
    debug=True,
    proxy_type="TRC",
    force_https="NO",
):
    return SolutionExposeDeployAutomated(
        type=type,
        solution_to_expose=solution_to_expose,
        domain=domain,
        sub_domain=sub_domain,
        tls_port=tls_port,
        port=port,
        debug=debug,
        proxy_type=proxy_type,
        force_https=force_https,
    )


def create_pool(
    solution_name, wallet_name, farm="Freefarm", cu=1, su=1, ipv4u=0, time_unit="Day", time_to_live=1, debug=True
):
    return PoolAutomated(
        solution_name=solution_name,
        wallet_name=wallet_name,
        farm=farm,
        cu=cu,
        su=su,
        ipv4u=ipv4u,
        time_unit=time_unit,
        time_to_live=time_to_live,
        debug=debug,
    )


def extend_pool(pool_id, wallet_name, cu=1, su=1, ipv4u=0, time_unit="Day", time_to_live=1, debug=True):
    return PoolExtendAutomated(
        pool_id=pool_id,
        wallet_name=wallet_name,
        cu=cu,
        su=su,
        ipv4u=ipv4u,
        time_unit=time_unit,
        time_to_live=time_to_live,
        debug=debug,
    )


def deploy_threebot(
    solution_name,
    ssh,
    secret,
    expiration,
    debug=True,
    domain_type="Automatically Get a Domain",
    domain_name=None,
    public_key="",
    email_host_user="",
    email_host="",
    email_host_password="",
    escalation_mail_address="",
    node_policy="Automatic",
    flavor="Silver (CPU 1 - Memory 2 GB - Disk 2 GB [SSD])",
):
    return ThreebotDeployAutomated(
        type="Create",
        ssh=ssh,
        solution_name=solution_name,
        secret=secret,
        expiration=expiration,
        debug=debug,
        domain_type=domain_type,
        domain_name=domain_name,
        public_key=public_key,
        email_host_user=email_host_user,
        email_host=email_host,
        email_host_password=email_host_password,
        escalation_mail_address=escalation_mail_address,
        node_policy=node_policy,
        flavor=flavor,
    )


def start_threebot(name, password):
    return ThreebotStart(tname=name, password=password,)


def change_threebot_size(name, password, flavor="Silver (CPU 1 - Memory 2 GB - Disk 2 GB [SSD])"):
    return ThreebotChangeSizeAutomated(tname=name, password=password, flavor=flavor)


def change_threebot_location(name, password, expiration_time, node_policy="Automatic"):
    return ThreebotChangeLocation(
        tname=name, password=password, node_policy=node_policy, expiration_time=expiration_time
    )
