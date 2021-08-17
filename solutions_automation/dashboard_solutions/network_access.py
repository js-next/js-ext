from jumpscale.packages.tfgrid_solutions.chats.network_access import NetworkAccess
from solutions_automation.utils.gedispatch import GedisChatBotPatch


class NetworkAccessAutomated(GedisChatBotPatch, NetworkAccess):
    IP_VERSION = "How would you like to connect to your network? If unsure, choose IPv4"
    ACCESS_NODE = "Please select an access node or leave it empty to automatically select it"
    NETWORK_NAME = "Please select a network to connect your solution to"
    POOL = "Please select a pool or leave it empty to automaically select it"

    QS = {
        IP_VERSION: "ip_version",
        ACCESS_NODE: "access_node",
        NETWORK_NAME: "network_name",
        POOL: "pool",
    }

    def ask(self, data):
        if data.get("msg"):
            self.md_show(data.get("msg"))
