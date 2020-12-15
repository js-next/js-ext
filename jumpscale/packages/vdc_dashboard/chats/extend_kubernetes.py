from jumpscale.loader import j
from jumpscale.sals.vdc.size import VDC_SIZE, INITIAL_RESERVATION_DURATION
from jumpscale.sals.chatflows.chatflows import GedisChatBot, StopChatFlow, chatflow_step
from jumpscale.sals.vdc.deployer import VDCIdentityError


class ExtendKubernetesCluster(GedisChatBot):
    title = "Extend Kubernetes Cluster"
    steps = ["flavor", "use_public_ip", "add_node", "success"]

    @chatflow_step(title="Node Size")
    def flavor(self):
        self.md_show_update("Checking payment service...")
        # check stellar service
        if not j.clients.stellar.check_stellar_service():
            raise StopChatFlow("Payment service is currently down, try again later")
        self.vdc_name = list(j.sals.vdc.list_all())[0]
        self.user_info_data = self.user_info()
        self.username = self.user_info_data["username"]
        self.vdc = j.sals.vdc.find(name=self.vdc_name, owner_tname=self.username)
        if not self.vdc:
            self.stop(f"VDC {self.vdc_name} doesn't exist")

        node_flavors = [flavor for flavor in VDC_SIZE.K8SNodeFlavor]

        node_flavor_messages = []
        for flavor in node_flavors:
            plan = VDC_SIZE.K8S_SIZES[flavor]
            node_flavor_messages.append(
                f"{flavor.name}: {plan['cru']} vCPU, {plan['mru']} GB Memory, {plan['sru']} GB SSD storage"
            )

        self.node_flavor = self.single_choice(
            "Choose the Node size", options=node_flavor_messages, default=node_flavor_messages[0], required=True
        )
        self.node_flavor = self.node_flavor.value.split(":")[0]

    @chatflow_step(title="Public IP")
    def use_public_ip(self):
        self.public_ip = self.single_choice(
            "Do you want to allow public ip for your node?", options=["No", "Yes"], default="No", required=True
        )
        if self.public_ip == "Yes":
            self.public_ip = True
        else:
            self.public_ip = False

    @chatflow_step(title="Adding node")
    def add_node(self):
        vdc_secret = self.secret_ask(f"Specify your VDC secret for {self.vdc_name}", min_length=8, required=True,)
        try:
            deployer = self.vdc.get_deployer(password=vdc_secret, bot=self)
        except VDCIdentityError:
            self.stop(
                f"Couldn't verify VDC secret. please make sure you are using the correct secret for VDC {self.vdc_name}"
            )

        success, amount, payment_id = self.vdc.show_external_node_payment(self, self.node_flavor, expiry=1)
        if not success:
            self.stop(f"payment timedout")

        self.md_show_update("Payment successful")
        initialization_wallet_name = j.core.config.get("VDC_INITIALIZATION_WALLET")
        old_wallet = deployer._set_wallet(initialization_wallet_name)
        wids = deployer.add_k8s_nodes(self.node_flavor, public_ip=self.public_ip)
        if not wids:
            j.sals.billing.issue_refund(payment_id)
            self.stop("failed to add nodes to your cluster. please contact support")
        self.md_show_update("Processing transaction...")
        initial_transaction_hashes = deployer.transaction_hashes
        try:
            self.vdc.transfer_to_provisioning_wallet(amount / 2)
        except Exception as e:
            j.logger.error(
                f"failed to fund provisioning wallet due to error {str(e)} for vdc: {self.vdc.vdc_name}. please contact support"
            )
            raise StopChatFlow(f"failed to fund provisioning wallet due to error {str(e)}")

        if initialization_wallet_name:
            try:
                self.vdc.pay_initialization_fee(initial_transaction_hashes, initialization_wallet_name)
            except Exception as e:
                j.logger.critical(f"failed to pay initialization fee for vdc: {self.vdc.solution_uuid}")
        deployer._set_wallet(old_wallet)
        self.md_show_update(f"updating pool expiration...")
        deployer.extend_k8s_workloads(14 - (INITIAL_RESERVATION_DURATION / 24), *wids)

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        self.md_show(f"""# You VDC {self.vdc_name} has been extended successfuly""")


chat = ExtendKubernetesCluster
