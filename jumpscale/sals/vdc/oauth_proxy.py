from .base_component import VDCBaseComponent
from jumpscale.loader import j
import gevent
import tempfile

from jumpscale.packages.vdc_dashboard.sals.solutions_chatflow import HELM_REPOS


class VDCOauthProxy(VDCBaseComponent):
    HELM_REPO_NAME = "marketplace"

    def deploy_chart(self, port="8080"):
        self.vdc_deployer.info("Initializing oauth proxy")

        try:
            helm_repos_urls = [repo["url"] for repo in self.vdc_deployer.vdc_k8s_manager.list_helm_repos()]
        except Exception as e:
            j.logger.warning(f"The following error happened with helm:\n {str(e)}")
            helm_repos_urls = []
        if HELM_REPOS[self.HELM_REPO_NAME]["url"] not in helm_repos_urls:
            self.vdc_deployer.info(f"Adding helm repo: {self.HELM_REPO_NAME}")
            self.vdc_deployer.vdc_k8s_manager.add_helm_repo(
                HELM_REPOS[self.HELM_REPO_NAME]["name"], HELM_REPOS[self.HELM_REPO_NAME]["url"]
            )
        self.vdc_deployer.vdc_k8s_manager.update_repos()

        self.vdc_deployer.info(f"Installing oauth proxy helm chart")
        self.vdc_instance.load_info()
        extra_config = {"ingress.host": self.vdc_instance.threebot.domain, "oauthproxyServerPort": str(port)}

        self.vdc_deployer.vdc_k8s_manager.install_chart(
            release="oauth-proxy",
            chart_name=f"{self.HELM_REPO_NAME}/oauth-proxy",
            namespace=f"oauth-proxy",
            extra_config=extra_config,
        )
