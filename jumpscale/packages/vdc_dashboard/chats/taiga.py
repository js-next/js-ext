from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.packages.vdc_dashboard.sals.solutions_chatflow import SolutionsChatflowDeploy


class TaigaDeploy(SolutionsChatflowDeploy):
    SOLUTION_TYPE = "taiga"
    title = "Taiga"
    HELM_REPO_NAME = "marketplace"
    steps = ["get_release_name", "create_subdomain", "set_config", "install_chart", "initializing", "success"]
    CHART_LIMITS = {
        "Silver": {"cpu": "3000m", "memory": "3024Mi"},
        "Gold": {"cpu": "4000m", "memory": "4096Mi"},
        "Platinum": {"cpu": "5000m", "memory": "5120Mi"},
    }

    @chatflow_step(title="Configurations")
    def set_config(self):

        self._choose_flavor()
        self.chart_config.update(
            {
                "domain": self.domain,
                "resources.cpu": self.resources_limits["cpu"][:-1],  # remove units added in chart
                "resources.memory": self.resources_limits["memory"][:-2],  # remove units added in chart
            }
        )


chat = TaigaDeploy
