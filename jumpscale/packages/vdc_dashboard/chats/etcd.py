import gevent
from textwrap import dedent
from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.vdc_dashboard.sals.solutions_chatflow import SolutionsChatflowDeploy, POD_INITIALIZING_TIMEOUT
from jumpscale.packages.vdc_dashboard.sals.vdc_dashboard_sals import get_deployments
from time import time

CHART_LIMITS = {
    "Silver": {"cpu": "100m", "memory": "128Mi", "no_nodes": "1", "volume_size": "2Gi"},
    "Gold": {"cpu": "100m", "memory": "128Mi", "no_nodes": "3", "volume_size": "4Gi"},
    "Platinum": {"cpu": "250m", "memory": "256Mi", "no_nodes": "3", "volume_size": "8Gi"},
}

RESOURCE_VALUE_TEMPLATE = {
    "cpu": "CPU {}",
    "memory": "Memory {}",
    "no_nodes": "Number of Nodes {}",
    "volume_size": "Volume {}",
}


class EtcdDeploy(SolutionsChatflowDeploy):
    SOLUTION_TYPE = "etcd"
    title = "ETCD"
    HELM_REPO_NAME = "marketplace"
    steps = ["get_release_name", "create_subdomain", "set_config", "install_chart", "initializing", "success"]

    @chatflow_step(title="Configurations")
    def set_config(self):
        username = self.user_info()["username"]
        # Check if entrypoint already added before with another deployment
        if not get_deployments(self.SOLUTION_TYPE, username):
            self.vdc.get_deployer().kubernetes.add_traefik_entrypoint("etcd", "2379")

        self._choose_flavor(CHART_LIMITS, RESOURCE_VALUE_TEMPLATE)
        self.chart_config.update(
            {
                "statefulset.replicaCount": self.resources_limits["no_nodes"],
                "resources.limits.cpu": self.resources_limits["cpu"],
                "resources.limits.memory": self.resources_limits["memory"],
                "persistence.size": self.resources_limits["volume_size"],
                "auth.rbac.enabled": "false",
                "metrics.enabled": "true",
                "ingress.host": self.domain,
            }
        )

    @chatflow_step(title="Initializing", disable_previous=True)
    def initializing(self):
        error_message_template = f"""\
                Failed to initialize {self.SOLUTION_TYPE}, please contact support with this information:

                Domain: {self.domain}
                VDC Name: {self.vdc_name}
                Farm name: {self.vdc_info["farm_name"]}
                Reason: {{reason}}
                """
        start_time = time()
        while time() - start_time <= POD_INITIALIZING_TIMEOUT:
            if self.chart_pods_started():
                break
            gevent.sleep(1)

        if not self.chart_pods_started() and self.chart_resource_failure():
            stop_message = error_message_template.format(
                reason="Couldn't find resources in the cluster for the solution"
            )
            self.k8s_client.delete_deployed_release(self.release_name)
            self.stop(dedent(stop_message))

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        domain_message = f'- You can access it through this url: <a href="https://{self.domain}" target="_blank">https://{self.domain}</a> as follow:<br />\n'
        message = f"""\
        # You deployed a new instance {self.release_name} of {self.SOLUTION_TYPE}
        <br />\n
        {domain_message}
        `etcdctl --endpoints=https://{self.domain}:2379 put hello Threefold`
        <br />\n
        `OK` will appear as confirmation message.

        - You can visit <a href="https://etcd.io/docs/v3.4.0/" target="_blank">ETCD Docs</a> for more information
        """
        self.md_show(dedent(message), md=True)


chat = EtcdDeploy