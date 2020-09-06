from jumpscale.sals.chatflows.chatflows import chatflow_step, StopChatFlow
from jumpscale.sals.marketplace import MarketPlaceAppsChatflow, deployer


class Peertube(MarketPlaceAppsChatflow):
    FLIST_URL = "https://hub.grid.tf/omar0.3bot/omarelawady-peertube-latest.flist"
    SOLUTION_TYPE = "peertube"
    steps = [
        "get_solution_name",
        "volume_details",
        "solution_expiration",
        "payment_currency",
        "infrastructure_setup",
        "reservation",
        "initializing",
        "success",
    ]

    title = "Peertube"
    query = {"cru": 1, "mru": 1, "sru": 1}

    @chatflow_step(title="Volume details")
    def volume_details(self):
        self._choose_flavor()
        self.vol_size = self.flavor_resources["sru"]
        self.vol_mount_point = "/var/www/peertube/storage/"
        self.query["sru"] += self.vol_size
        self.user_email = self.user_info()["email"]

    @chatflow_step(title="Reservation", disable_previous=True)
    def reservation(self):
        metadata = {
            "name": self.solution_name,
            "form_info": {"chatflow": self.SOLUTION_TYPE, "Solution name": self.solution_name},
        }
        self.solution_metadata.update(metadata)

        # deploy volume
        vol_id = deployer.deploy_volume(
            self.pool_id,
            self.selected_node.node_id,
            self.vol_size,
            solution_uuid=self.solution_id,
            **self.solution_metadata,
        )
        success = deployer.wait_workload(vol_id, self)
        if not success:
            raise StopChatFlow(f"Failed to deploy volume on node {self.selected_node.node_id} {vol_id}")
        volume_config = {self.vol_mount_point: vol_id}

        # reserve subdomain
        _id = deployer.create_subdomain(
            pool_id=self.pool_id,
            gateway_id=self.gateway.node_id,
            subdomain=self.domain,
            addresses=self.addresses,
            solution_uuid=self.solution_id,
            **self.solution_metadata,
        )

        success = deployer.wait_workload(_id, self)
        if not success:
            raise StopChatFlow(f"Failed to create subdomain {self.domain} on gateway" f" {self.gateway.node_id} {_id}")
        self.threebot_url = f"http://{self.domain}"

        entrypoint = f'/usr/local/bin/startup.sh "{self.domain}"'
        self.entrypoint = entrypoint
        # reserve container
        self.resv_id = deployer.deploy_container(
            pool_id=self.pool_id,
            node_id=self.selected_node.node_id,
            network_name=self.network_view.name,
            ip_address=self.ip_address,
            flist=self.FLIST_URL,
            cpu=self.query["cru"],
            memory=self.query["mru"] * 1024,
            disk_size=(self.query["sru"] - self.vol_size) * 1024,
            entrypoint=entrypoint,
            volumes=volume_config,
            interactive=False,
            **self.solution_metadata,
            solution_uuid=self.solution_id,
        )
        success = deployer.wait_workload(self.resv_id, self)
        if not success:
            raise StopChatFlow(f"Failed to deploy workload {self.resv_id}")

        _id = deployer.expose_and_create_certificate(
            pool_id=self.pool_id,
            gateway_id=self.gateway.node_id,
            network_name=self.network_view.name,
            trc_secret=self.secret,
            domain=self.domain,
            email=self.user_email,
            solution_ip=self.ip_address,
            solution_port=80,
            enforce_https=True,
            node_id=self.selected_node.node_id,
            solution_uuid=self.solution_id,
            proxy_pool_id=self.gateway_pool.pool_id,
            **self.solution_metadata,
        )
        success = deployer.wait_workload(_id, self)
        if not success:
            # FIXME
            # solutions.cancel_solution(self.user_info()["username"], self.workload_ids)
            raise StopChatFlow(f"Failed to create TRC container on node {self.selected_node.node_id} {_id}")


chat = Peertube
