from jumpscale.sals.vdc.size import PREFERED_FARM
from jumpscale.loader import j
from jumpscale.sals.vdc.size import VDC_SIZE, INITIAL_RESERVATION_DURATION
from jumpscale.sals.vdc.proxy import VDC_PARENT_DOMAIN
from jumpscale.sals.chatflows.chatflows import GedisChatBot, chatflow_step, StopChatFlow
from textwrap import dedent
import uuid
from urllib.parse import urlparse

MINIMUM_ACTIVATION_XLMS = 0


class VDCDeploy(GedisChatBot):
    title = "VDC"
    steps = ["vdc_info", "deploy", "initializing", "success"]

    def _init(self):
        self.md_show_update("It will take a few seconds to be ready to help you ...")
        # check stellar service
        if not j.clients.stellar.check_stellar_service():
            raise StopChatFlow("Payment service is currently down, try again later")
        # xlms check
        for wname in ["activation_wallet"]:
            if wname in j.clients.stellar.list_all():
                try:
                    w = j.clients.stellar.get(wname)
                    if w.get_balance_by_asset("XLM") < 10:
                        raise StopChatFlow(f"{wname} doesn't have enough XLM to support the deployment.")
                except:
                    raise StopChatFlow(f"couldn't get the balance for {wname} wallet")
                else:
                    j.logger.info(f"{wname} is funded")
            else:
                j.logger.info(f"this system doesn't have {wname} configured")

        # tft wallets check
        for wname in ["vdc_init", "grace_period"]:
            try:
                w = j.clients.stellar.get(wname)
                if w.get_balance_by_asset() < 50:
                    raise StopChatFlow(f"{wname} doesn't have enough TFT to support the deployment.")
            except:
                raise StopChatFlow(f"couldn't get the balance for {wname} wallet")
            else:
                j.logger.info(f"{wname} is funded")

        self.user_info_data = self.user_info()
        self.username = self.user_info_data["username"]

    def _vdc_form(self):
        vdc_names = [vdc.vdc_name for vdc in j.sals.vdc.list(self.username, load_info=True) if not vdc.is_empty()]
        vdc_flavors = [flavor for flavor in VDC_SIZE.VDC_FLAVORS]
        vdc_flavor_messages = []
        for flavor in vdc_flavors:
            plan = VDC_SIZE.VDC_FLAVORS[flavor]
            kubernetes_plan = VDC_SIZE.K8S_SIZES[plan["k8s"]["size"]]
            zdb_size = VDC_SIZE.S3_ZDB_SIZES[plan["s3"]["size"]]["sru"]
            zdb_human_readable_size = zdb_size if zdb_size < 1000 else zdb_size / 1024
            zdb_identifier = "GB" if zdb_size < 1000 else "TB"
            zdb_limit = plan["s3"]["upto"]
            no_nodes = plan["k8s"]["no_nodes"]
            ntft = float(VDC_SIZE.PRICES["plans"][flavor])
            ndollars = round(ntft / 10)
            vdc_flavor_messages.append(
                f"{flavor.name}: Kubernetes cluster (small controller, {no_nodes} worker(s) {kubernetes_plan['cru']} vCPU, {kubernetes_plan['mru']} GB Memory, {kubernetes_plan['sru']} GB SSD Storage)"
                f", ZDB Storage ({zdb_limit}) for {ndollars} USD/Month = {ntft} TFT/Month "
            )
        form = self.new_form()
        self.vdc_name = form.string_ask(
            "Please enter a name for your VDC (will be used in listing and deletions in the future and in having a unique url)",
            required=True,
            not_exist=["VDC", vdc_names],
            is_identifier=True,
            max_length=20,
        )
        self.vdc_secret = form.secret_ask("VDC Secret (Secret for controlling the vdc)", min_length=8, required=True)
        self.vdc_flavor = form.single_choice(
            "Choose the VDC plan", options=vdc_flavor_messages, default=vdc_flavor_messages[0], required=True
        )
        # self.deployment_logs = form.single_choice("Enable extensive deployment logs?", ["Yes", "No"], default="No")
        form.ask()
        self.restore = False
        vdc = j.sals.vdc.find(vdc_name=self.vdc_name.value, owner_tname=self.username)
        if vdc:
            self.restore = True
            j.logger.info(f"deleting empty vdc instance: {vdc.instance_name} with uuid: {vdc.solution_uuid}")
            j.sals.vdc.delete(vdc.instance_name)

        self.vdc_flavor = self.vdc_flavor.value.split(":")[0]

    def _k3s_and_minio_form(self):
        form = self.new_form()
        self.minio_access_key = form.string_ask(
            "S3 access key (Credentials used to access the VDC's S3)", required=True
        )
        self.minio_secret_key = form.secret_ask(
            "S3 secret key (Credentials used to access the VDC's S3)", min_length=8, required=True
        )
        form.ask()

    def _backup_form(self):
        valid = False
        while not valid:
            form = self.new_form()
            if self.restore:
                self.s3_url = form.string_ask(
                    "S3 URL to restore your k8s cluster (eg: http://s3.webg1test.grid.tf/)", required=True
                )
            else:
                self.s3_url = form.string_ask(
                    "S3 URL to back your k8s cluster to (eg: http://s3.webg1test.grid.tf/)", required=True
                )
            self.s3_region = form.string_ask("S3 region name (eg: minio in case you are using minio)", required=True)
            self.s3_bucket = form.string_ask(
                "S3 bucket name (make sure the bucket policy is Read/Write)", required=True
            )
            self.ak = form.string_ask("S3 access key (S3 credentials)", required=True)
            self.sk = form.secret_ask("S3 secret key (S3 credentials)", required=True)
            form.ask()
            self.backup_config = {
                "ak": self.ak.value,
                "sk": self.sk.value,
                "region": self.s3_region.value,
                "url": self.s3_url.value,
                "bucket": self.s3_bucket.value,
            }
            valid, msg = self._validate_s3_config()
            if not valid:
                self.md_show(f"{msg}. please try again")

    def _validate_s3_config(self):
        try:
            res = urlparse(self.backup_config["url"])
        except Exception as e:
            return False, f"invalid url. {str(e)}"
        if res.scheme not in ["http", "https"]:
            return False, "invalid scheme. can be either http or https"
        # TODO: validate bucket existence and policy?
        return True, ""

    @chatflow_step(title="VDC Information")
    def vdc_info(self):
        self._init()
        self._vdc_form()
        self.backup_config = None
        # self._backup_form()
        # self._k3s_and_minio_form() # TODO: Restore later

    @chatflow_step(title="VDC Deployment")
    def deploy(self):
        self.vdc = j.sals.vdc.new(
            vdc_name=self.vdc_name.value, owner_tname=self.username, flavor=VDC_SIZE.VDCFlavor[self.vdc_flavor]
        )
        try:
            self.vdc.prepaid_wallet
            self.vdc.provision_wallet
        except Exception as e:
            j.sals.vdc.delete(self.vdc.instance_name)
            j.logger.error(f"failed to initialize wallets for VDC {self.vdc_name.value} due to error {str(e)}")
            self.stop(f"failed to initialize VDC wallets. please try again later")

        try:
            self.deployer = self.vdc.get_deployer(password=self.vdc_secret.value, bot=self)
        except Exception as e:
            j.logger.error(f"failed to initialize VDC deployer due to error {str(e)}")
            j.sals.vdc.delete(self.vdc.instance_name)
            self.stop("failed to initialize VDC deployer. please contact support")

        farm_name = PREFERED_FARM.get()  # TODO: use the selected farm name when users are allowed to select farms
        if not self.deployer.check_capacity(farm_name):
            raise StopChatFlow(
                f"There are not enough resources available to deploy your VDC of flavor `{self.deployer.flavor.value}`. To restart VDC creation, please use the refresh button on the upper right corner."
            )
        prefix = self.deployer.get_prefix()
        subdomain = f"{prefix}.{VDC_PARENT_DOMAIN}"
        j.logger.info(f"checking the availability of subdomain {subdomain}")
        if self.deployer.proxy.check_domain_availability(subdomain):
            j.logger.info(f"subdomain {subdomain} is resolvable. checking owner info")
            if not self.deployer.proxy.check_subdomain_existence(subdomain):
                j.logger.warning(f"subdomain {subdomain} is not owned by vdc identity: {self.deployer.identity.tid}")
                uid = self.deployer.proxy.check_subdomain_owner(subdomain)
                if uid:
                    j.logger.error(f"Subdomain {subdomain} is owned by identity {uid}")
                    raise StopChatFlow(
                        f"Subdomain {subdomain} is not available. please use a different name for your vdc"
                    )
                else:
                    j.logger.warning(
                        f"Subdomain {subdomain} is not reserved on the explorer. continuing with the deployment."
                    )

        success, amount, payment_id = self.vdc.show_vdc_payment(self)
        if not success:
            j.sals.vdc.delete(self.vdc.instance_name)  # delete it?
            self.stop(f"payment timedout")
        self.md_show_update("Payment successful")

        self.md_show_update("Deploying your VDC...")
        initialization_wallet_name = j.core.config.get("VDC_INITIALIZATION_WALLET")
        old_wallet = self.deployer._set_wallet(initialization_wallet_name)
        try:
            self.config = self.deployer.deploy_vdc(
                minio_ak=None, minio_sk=None, s3_backup_config=self.backup_config, install_oauth_proxy=True
            )
            if not self.config:
                raise StopChatFlow("Failed to deploy VDC due to invlaid kube config. please try again later")
            self.public_ip = self.vdc.kubernetes[0].public_ip
        except Exception as err:
            j.logger.error(str(err))
            self.deployer.rollback_vdc_deployment()
            j.sals.billing.issue_refund(payment_id)
            j.sals.vdc.delete(self.vdc.vdc_name)
            self.stop(str(err))
        self.md_show_update("Adding funds to provisioning wallet...")
        initial_transaction_hashes = self.deployer.transaction_hashes
        try:
            self.vdc.transfer_to_provisioning_wallet(amount / 2)
        except Exception as e:
            j.sals.billing.issue_refund(payment_id)
            j.sals.vdc.delete(self.vdc.instance_name)
            j.logger.error(f"failed to fund provisioning wallet due to error {str(e)} for vdc: {self.vdc.vdc_name}.")
            raise StopChatFlow(f"failed to fund provisioning wallet due to error {str(e)}")

        if initialization_wallet_name:
            try:
                self.vdc.pay_initialization_fee(initial_transaction_hashes, initialization_wallet_name)
            except Exception as e:
                j.logger.critical(f"failed to pay initialization fee for vdc: {self.vdc.solution_uuid}")
        self.deployer._set_wallet(old_wallet)
        self.md_show_update("Funding difference...")
        self.vdc.fund_difference(initialization_wallet_name)
        self.md_show_update("Updating expiration...")
        self.deployer.renew_plan(14 - INITIAL_RESERVATION_DURATION / 24)

    @chatflow_step(title="Initializing", disable_previous=True)
    def initializing(self):
        threebot_url = f"https://{self.vdc.threebot.domain}/"
        self.md_show_update(
            f"Initializing your VDC 3Bot container at {threebot_url} ... ip: {self.vdc.threebot.ip_address}. public: {self.vdc.kubernetes[0].public_ip}"
        )
        if not j.sals.reservation_chatflow.wait_http_test(
            threebot_url, timeout=600, verify=not j.config.get("TEST_CERT")
        ):
            self.stop(f"Failed to initialize VDC on {threebot_url} , please contact support")

    @chatflow_step(title="VDC Deployment Success", final_step=True)
    def success(self):
        msg = dedent(
            f"""\
        # Your VDC {self.vdc.vdc_name} has been deployed successfully.
        <br />\n
        You can download the kubeconfig file from the dashboard to ~/.kube/config to start using your cluster with kubectl

        Kubernetes controller public IP: {self.public_ip}
        <br />\n
        """
        )
        self.md_show(dedent(msg), md=True)


chat = VDCDeploy
