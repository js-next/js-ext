from jumpscale.packages.tfgrid_solutions.chats.flist import FlistDeploy
from solutions_automation.utils.gedispatch import GedisChatBotPatch
from jumpscale.loader import j


class FlistAutomated(GedisChatBotPatch, FlistDeploy):
    NAME_MESSAGE = "Please enter a name for your workload (Can be used to prepare domain for you and needed to track your solution on the grid)"
    CPU_MESSAGE = "Please specify how many CPUs"
    MEM_MESSAGE = "Please specify how much memory (in MB)"
    DISK_SIZE_MESSAGE = "Please specify the size of root filesystem (in MB)"
    VOLUME_MESSAGE = "Would you like to attach an extra volume to the container"
    FLIST_MESSGAE = "Please add the link to your flist to be deployed."
    ENV_VARS = "Set Environment Variables"
    COREX_MESSAGE = "Would you like access to your container through the web browser (coreX)?"
    ENTRY_POINT = "Please add your entrypoint for your flist"
    NETWORK_MESSAGE = "Please select a network to connect your solution to"
    LOG_MESSAGE = "Do you want to push the container logs (stdout and stderr) onto an external redis channel"
    IP_MESSAGE = "Please choose IP Address for your solution"
    IPV6_MESSAGE = r"^Do you want to assign a global IPv6 address to (.*)\?$"
    NODE_ID_MESSAGE = r"^Do you want to automatically select a node to deploy (.*)\?$"
    POOL_MESSAGE = r"^Please select a pool( for (.*))?$"
    NODE_SELECTION_MESSAGE = r"^Please choose the node you want to deploy (.*) on$"
    REDIS_CHANNEL_TYPE = "Please add the channel type"
    REDIS_IP = "Please add the IP address where the logs will be output to"
    REDIS_PORT = "Please add the port available where the logs will be output to"
    REDIS_CHANNEL_NAME = (
        "Please add the channel name to be used. The channels will be in the form NAME-stdout and NAME-stderr"
    )

    QS = {
        # strs
        NAME_MESSAGE: "get_name",
        FLIST_MESSGAE: "flist",
        ENTRY_POINT: "entry_point",
        REDIS_CHANNEL_TYPE: "redis_chaneel_type",
        REDIS_IP: "redis_ip",
        REDIS_PORT: "redis_port",
        REDIS_CHANNEL_NAME: "redis_channel_name",
        # ints
        CPU_MESSAGE: "cpu",
        MEM_MESSAGE: "memory",
        DISK_SIZE_MESSAGE: "disk_size",
        # single choice
        VOLUME_MESSAGE: "vol",
        COREX_MESSAGE: "corex",
        NETWORK_MESSAGE: "network",
        LOG_MESSAGE: "log",
        IP_MESSAGE: "ipv4",
        IPV6_MESSAGE: "ipv6",
        POOL_MESSAGE: "pool",
        NODE_ID_MESSAGE: "node_automatic",
        NODE_SELECTION_MESSAGE: "node",
        # multi value ask
        ENV_VARS: "env_vars",
    }

    def single_choice(self, msg, *args, **kwargs):
        selected = self.fetch_param(msg, *args, **kwargs)
        if args:
            for m in args[0]:
                if str(selected) in m:
                    return m
        return selected

    def md_show(self, msg, *args, **kwargs):
        if self.debug:
            if "This flist doesn't exist. Please make sure you enter a valid link to an existing flist" in msg:
                raise RuntimeError(msg)
            j.logger.info(msg)
