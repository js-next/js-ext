from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import StopChatFlow, chatflow_step
from jumpscale.sals.reservation_chatflow import deployer, deployment_context, solutions
from jumpscale.packages.tfgrid_solutions.sals.network_chat_base import NetworkBase


class NetworkDeploy(NetworkBase):
    title = "Network"

    def _init(self):
        self.md_show_update("Initializing chatflow...")
        deployer.chatflow_pools_check()
        self.solution_metadata = {}

    @chatflow_step(title="Network Name")
    def start(self):
        super().start()
        valid = False
        while not valid:
            self.solution_name = deployer.ask_name(
                self, "Please enter a name for your workload (Needed to track your solution on the grid)"
            )
            network_solutions = solutions.list_network_solutions(sync=False)
            valid = True
            for sol in network_solutions:
                if sol["Name"] == self.solution_name:
                    valid = False
                    self.md_show("The specified solution name already exists. please choose another name.")
                    break
                valid = True

    @chatflow_step(title="IP Configuration", payment=True)  # TODO: remove the payment, "testing"
    def ip_config(self):
        self.ip_range = j.sals.reservation_chatflow.reservation_chatflow.get_ip_range(self)
        ips = ["IPv6", "IPv4"]
        self.ipversion = self.single_choice(
            "How would you like to connect to your network? If unsure, choose IPv4", ips, required=True, default="IPv4",
        )

    @chatflow_step(title="Reservation", deployment=True)
    @deployment_context()
    def network_reservation(self):
        try:
            self.config = deployer.deploy_network(
                self.solution_name,
                self.access_node,
                self.ip_range,
                self.ipversion,
                self.pool,
                **self.solution_metadata,
            )
        except Exception as e:
            raise StopChatFlow(f"Failed to register workload due to error {str(e)}")

        super().network_reservation()


chat = NetworkDeploy
