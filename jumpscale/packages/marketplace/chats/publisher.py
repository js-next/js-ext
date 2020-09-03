from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import chatflow_step
from jumpscale.sals.marketplace import MarketPlaceAppsChatflow, deployer, solutions
from jumpscale.sals.reservation_chatflow import deployment_context, DeploymentFailed


class Publisher(MarketPlaceAppsChatflow):
    FLIST_URL = "https://hub.grid.tf/ahmed_hanafy_1/ahmedhanafy725-pubtools-trc.flist"
    SOLUTION_TYPE = "publisher"  # chatflow used to deploy the solution
    title = "Publisher"
    steps = [
        "get_solution_name",
        "configuration",
        "solution_expiration",
        "payment_currency",
        "infrastructure_setup",
        "deploy",
        "initializing",
        "success",
    ]

    storage_url = "zdb://hub.grid.tf:9900"
    query = {"cru": 1, "mru": 1, "sru": 2}

    @chatflow_step(title="Solution Settings")
    def configuration(self):
        form = self.new_form()
        ttype = form.single_choice("Choose the type", options=["wiki", "www", "blog"], default="wiki", required=True)
        title = form.string_ask("Title", required=True)
        url = form.string_ask("Repository url", required=True)
        branch = form.string_ask("Branch", required=True)
        form.ask("Set configuration")
        self.username = self.user_info()["username"]
        self.user_email = self.user_info()["email"]
        self.envars = {
            "TYPE": ttype.value,
            "NAME": "entrypoint",
            "TITLE": title.value,
            "URL": url.value,
            "BRANCH": branch.value,
            "EMAIL": self.user_email,
        }

    @chatflow_step(title="Reservation", disable_previous=True)
    @deployment_context()
    def deploy(self):
        metadata = {
            "name": self.solution_name,
            "form_info": {"Solution name": self.solution_name, "chatflow": self.SOLUTION_TYPE},
        }
        self.solution_metadata.update(metadata)
        self.workload_ids = []
        self.network_view = self.network_view.copy()
        result = deployer.add_network_node(
            self.network_view.name,
            self.selected_node,
            self.pool_id,
            self.network_view,
            bot=self,
            owner=self.solution_metadata.get("owner"),
        )
        if result:
            for wid in result["ids"]:
                success = deployer.wait_workload(wid, self, breaking_node_id=self.selected_node.node_id)
                if not success:
                    raise DeploymentFailed(f"Failed to add node {self.selected_node.node_id} to network {wid}")
        self.network_view_copy = self.network_view.copy()
        self.ip_address = self.network_view_copy.get_free_ip(self.selected_node)

        # 2- reserve subdomain
        self.workload_ids.append(
            deployer.create_subdomain(
                pool_id=self.gateway_pool.pool_id,
                gateway_id=self.gateway.node_id,
                subdomain=self.domain,
                addresses=self.addresses,
                solution_uuid=self.solution_id,
                **self.solution_metadata,
            )
        )
        success = deployer.wait_workload(self.workload_ids[0], self)
        if not success:
            raise DeploymentFailed(
                f"Failed to create subdomain {self.domain} on gateway {self.gateway.node_id} {self.workload_ids[0]}"
            )

        # 3- reserve tcp proxy
        self.workload_ids.append(
            deployer.create_proxy(
                pool_id=self.gateway_pool.pool_id,
                gateway_id=self.gateway.node_id,
                domain_name=self.domain,
                trc_secret=self.secret,
                solution_uuid=self.solution_id,
                **self.solution_metadata,
            )
        )
        success = deployer.wait_workload(self.workload_ids[1], self)
        if not success:
            solutions.cancel_solution(self.username, self.workload_ids)
            raise DeploymentFailed(
                f"Failed to create reverse proxy {self.domain} on gateway {self.gateway.node_id} {self.workload_ids[1]}",
                solution_uuid=self.solution_id,
            )

        # 4- deploy container
        self.envars["TRC_REMOTE"] = f"{self.gateway.dns_nameserver[0]}:{self.gateway.tcp_router_port}"
        self.envars["DOMAIN"] = self.domain
        self.envars["TEST_CERT"] = "true" if j.config.get("TEST_CERT") else "false"
        secret_env = {"TRC_SECRET": self.secret}
        self.workload_ids.append(
            deployer.deploy_container(
                pool_id=self.pool_id,
                node_id=self.selected_node.node_id,
                network_name=self.network_view.name,
                ip_address=self.ip_address,
                flist=self.FLIST_URL,
                env=self.envars,
                cpu=self.query["cru"],
                memory=self.query["mru"] * 1024,
                disk_size=self.query["sru"] * 1024,
                entrypoint="/bin/bash /start.sh",
                secret_env=secret_env,
                interactive=False,
                solution_uuid=self.solution_id,
                public_ipv6=True,
                **self.solution_metadata,
            )
        )
        self.resv_id = self.workload_ids[-1]
        if not success:
            solutions.cancel_solution(self.username, self.workload_ids)
            raise DeploymentFailed(
                f"Failed to create container on node {self.selected_node.node_id} {self.workload_ids[2]}",
                solution_uuid=self.solution_id,
            )


chat = Publisher
