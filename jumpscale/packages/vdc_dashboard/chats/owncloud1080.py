from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.vdc_dashboard.sals.solutions_chatflow import SolutionsChatflowDeploy


class OwncloudDeploy(SolutionsChatflowDeploy):
    SOLUTION_TYPE = "owncloud-1080"
    title = "Owncloud 10.8.0"
    HELM_REPO_NAME = "marketplace"
    steps = [
        "init_chatflow",
        "get_release_name",
        "choose_flavor",
        "create_subdomain",
        "install_chart",
        "initializing",
        "success",
    ]

    def get_config(self):
        return {
            "ingress.hostname": self.config.chart_config.domain,
            "owncloudUsername": "admin",
            "owncloudPassword": "password",
            "mariadb.auth.rootPassword": "secretpassword",
        }

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        extra_info = f"Admin user credentials for owncloud is: \
    <br/> Username: admin<br/> Password: password<br/>Mariadb rootpassword: secretpassword<br/>Please consider changing them after login"
        super().success(extra_info=extra_info)


chat = OwncloudDeploy
