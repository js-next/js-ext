from gedispatch import GedisChatBotPatch
from jumpscale.packages.tfgrid_solutions.chats.flist import FlistDeploy
from time import time


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
    NETWORK_MESSAGE = "Please select a network"
    LOG_MESSAGE = "Do you want to push the container logs (stdout and stderr) onto an external redis channel"
    IP_MESSAGE = "Please choose IP Address for your solution"
    IPV6_MESSAGE = r"^Do you want to assign a global IPv6 address to (.*)\?$"
    NODE_ID_MESSAGE = r"^Do you want to automatically select a node for deployment for (.*)\?$"
    POOL_MESSAGE = r"^Please select a pool( for (.*))?$"
    NODE_SELECTION_MESSAGE = r"^Please choose the node you want to deploy (.*) on$"

    QS = {
        # strs
        NAME_MESSAGE: "get_name",
        FLIST_MESSGAE: "flist",
        ENTRY_POINT: "entry_point",
        # ints
        CPU_MESSAGE: "cpu",
        MEM_MESSAGE: "memory",
        DISK_SIZE_MESSAGE: "disk_size",
        # single choice
        VOLUME_MESSAGE: "vol",
        COREX_MESSAGE: "corex",
        NETWORK_MESSAGE: "choose_random",
        LOG_MESSAGE: "log",
        IP_MESSAGE: "choose_random",
        IPV6_MESSAGE: "ipv6",
        POOL_MESSAGE: "choose_random",
        NODE_ID_MESSAGE: "node_automatic",
        NODE_SELECTION_MESSAGE: "choose_random",
        # multi value ask
        ENV_VARS: "env_vars",
    }


FlistAutomated(
    solution_name="ubnutu",
    currency="TFT",
    flist="https://hub.grid.tf/tf-bootable/3bot-ubuntu-18.04.flist",
    cpu=1,
    memory=1024,
    disk_size=256,
    vol="NO",
    corex="YES",
    entry_point="",
    env_vars={"name": "TEST"},
    log="NO",
    ipv6="NO",
    node_automatic="NO",
    debug=True,
)
