from textwrap import dedent
from time import time

import gevent
from jumpscale.packages.vdc_dashboard.sals.solutions_chatflow import SolutionsChatflowDeploy
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.loader import j

POD_INITIALIZING_TIMEOUT = 120


class MinioDeploy(SolutionsChatflowDeploy):
    SOLUTION_TYPE = "minio"
    title = "Minio Quantum Storage"
    HELM_REPO_NAME = "marketplace"
    steps = [
        "get_release_name",
        "create_subdomain",
        "set_config",
        "quantum_storage",
        "install_chart",
        "initializing",
        "success",
    ]

    @chatflow_step(title="Configurations")
    def set_config(self):
        self.path = f"/home/rancher/{self.chart_name}{self.release_name}"

        form = self.new_form()
        accesskey = form.string_ask(
            "Please add the key to be used for minio when logging in. Make sure not to lose it",
            min_length=3,
            required=True,
        )
        secret = form.secret_ask(
            "Please add the secret to be used for minio when logging in to match the previous key. Make sure not to lose it",
            min_length=8,
            required=True,
        )
        form.ask()

        self.chart_config.update(
            {
                "ingress.host": self.domain,
                "accessKey": accesskey.value,
                "secretKey": secret.value,
                "volume.hostPath": self.path,
            }
        )

    @chatflow_step(title="Quantum Storage")
    def quantum_storage(self):
        self.md_show_update("Initializing Quantum Storage, This may take few seconds ...")
        qs = self.vdc.get_quantumstorage_manager()
        qs.apply(self.path)

    @chatflow_step(title="Initializing", disable_previous=True)
    def initializing(self, timeout=300):
        self.md_show_update(f"Initializing your {self.SOLUTION_TYPE}...")
        domain_message = ""
        if self._has_domain():
            domain_message = f"Domain: {self.domain}"
        error_message_template = f"""\
                Failed to initialize {self.SOLUTION_TYPE}, please contact support with this information:

                {domain_message}
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
            self.k8s_client.execute_native_cmd(f"kubectl delete ns {self.chart_name}-{self.release_name}")
            self.stop(dedent(stop_message))

        if self._has_domain() and not j.sals.reservation_chatflow.wait_http_test(
            f"https://{self.domain}", timeout=timeout - POD_INITIALIZING_TIMEOUT, verify=False, status_code=403
        ):
            stop_message = error_message_template.format(reason="Couldn't reach the website after deployment")
            self.stop(dedent(stop_message))
        self._label_resources(backupType="vdc")


chat = MinioDeploy