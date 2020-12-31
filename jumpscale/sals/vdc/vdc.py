import datetime
from decimal import Decimal
import uuid

from jumpscale.clients.explorer.models import NextAction, WorkloadType
from jumpscale.core.base import Base, fields
from jumpscale.loader import j
from jumpscale.sals.zos import get as get_zos

from .deployer import VDCDeployer
from .models import *
from .size import VDC_SIZE, PROXY_FARM, FARM_DISCOUNT
from .wallet import VDC_WALLET_FACTORY
import netaddr

VDC_WORKLOAD_TYPES = [
    WorkloadType.Container,
    WorkloadType.Zdb,
    WorkloadType.Kubernetes,
    WorkloadType.Subdomain,
    WorkloadType.Reverse_proxy,
]


class UserVDC(Base):
    vdc_name = fields.String()
    owner_tname = fields.String()
    solution_uuid = fields.String(default=lambda: uuid.uuid4().hex)
    identity_tid = fields.Integer()
    flavor = fields.Enum(VDC_SIZE.VDCFlavor)
    s3 = fields.Object(S3)
    kubernetes = fields.List(fields.Object(KubernetesNode))
    threebot = fields.Object(VDCThreebot)
    created = fields.DateTime(default=datetime.datetime.utcnow)
    last_updated = fields.DateTime(default=datetime.datetime.utcnow)
    is_blocked = fields.Boolean(default=False)  # grace period action is applied
    explorer_url = fields.String(default=lambda: j.core.identity.me.explorer_url)

    def is_empty(self):
        if any([self.kubernetes, self.threebot.wid, self.threebot.domain, self.s3.minio.wid, self.s3.zdbs]):
            return False
        return True

    @property
    def expiration_date(self):
        expiration = self.get_pools_expiration()
        return j.data.time.get(expiration).datetime

    @property
    def prepaid_wallet(self):
        wallet_name = f"prepaid_wallet_{self.solution_uuid}"
        wallet = j.clients.stellar.find(wallet_name)
        if not wallet:
            vdc_wallet = VDC_WALLET_FACTORY.find(wallet_name)
            if not vdc_wallet:
                vdc_wallet = VDC_WALLET_FACTORY.new(wallet_name)
                vdc_wallet.save()
            wallet = vdc_wallet.stellar_wallet
        return wallet

    @property
    def provision_wallet(self):
        wallet_name = f"provision_wallet_{self.solution_uuid}"
        wallet = j.clients.stellar.find(wallet_name)
        if not wallet:
            vdc_wallet = VDC_WALLET_FACTORY.find(wallet_name)
            if not vdc_wallet:
                vdc_wallet = VDC_WALLET_FACTORY.new(wallet_name)
                vdc_wallet.save()
            wallet = vdc_wallet.stellar_wallet
        return wallet

    @property
    def vdc_workloads(self):
        workloads = []
        workloads += self.kubernetes
        workloads += self.s3.zdbs
        if self.threebot.wid:
            workloads.append(self.threebot)
        if self.s3.minio.wid:
            workloads.append(self.s3.minio)
        return workloads

    @property
    def active_pools(self):
        my_pool_ids = [w.pool_id for w in self.vdc_workloads]
        explorer = j.core.identity.me.explorer
        active_pools = [p for p in explorer.pools.list(customer_tid=self.identity_tid) if p.pool_id in my_pool_ids]
        return active_pools

    def get_deployer(self, password=None, identity=None, bot=None, proxy_farm_name=None):
        proxy_farm_name = proxy_farm_name or PROXY_FARM.get()
        if not password and not identity:
            instance_name = f"vdc_ident_{self.solution_uuid}"
            if j.core.identity.find(instance_name):
                identity = j.core.identity.find(instance_name)
            else:
                identity = j.core.identity.me

        return VDCDeployer(
            vdc_instance=self, password=password, bot=bot, proxy_farm_name=proxy_farm_name, identity=identity
        )

    def load_info(self):
        self.kubernetes = []
        self.s3 = S3()
        self.threebot = VDCThreebot()
        instance_vdc_workloads = self._filter_vdc_workloads()
        subdomains = []
        proxies = []
        for workload in instance_vdc_workloads:
            self._update_instance(workload)
            if workload.info.workload_type == WorkloadType.Subdomain:
                subdomains.append(workload)
            if workload.info.workload_type == WorkloadType.Reverse_proxy:
                proxies.append(workload)
        self._get_s3_subdomains(subdomains)
        self._get_threebot_subdomain(proxies)

    def _filter_vdc_workloads(self):
        zos = get_zos()
        user_workloads = zos.workloads.list(self.identity_tid, next_action=NextAction.DEPLOY)
        result = []
        for workload in user_workloads:
            if workload.info.workload_type not in VDC_WORKLOAD_TYPES:
                continue
            if not workload.info.description:
                continue
            try:
                description = j.data.serializers.json.loads(workload.info.description)
            except:
                continue
            if description.get("vdc_uuid") != self.solution_uuid:
                continue
            result.append(workload)
        return result

    def _update_instance(self, workload):
        k8s_sizes = [
            VDC_SIZE.K8SNodeFlavor.SMALL.value,
            VDC_SIZE.K8SNodeFlavor.MEDIUM.value,
            VDC_SIZE.K8SNodeFlavor.BIG.value,
        ]
        if workload.info.workload_type == WorkloadType.Kubernetes:
            node = KubernetesNode()
            node.wid = workload.id
            node.ip_address = workload.ipaddress
            if workload.master_ips:
                node.role = KubernetesRole.WORKER
            else:
                node.role = KubernetesRole.MASTER
            node.node_id = workload.info.node_id
            node.pool_id = workload.info.pool_id
            if workload.public_ip:
                zos = get_zos()
                public_ip_workload = zos.workloads.get(workload.public_ip)
                address = str(netaddr.IPNetwork(public_ip_workload.ipaddress).ip)
                node.public_ip = address

            node.size = (
                VDC_SIZE.K8SNodeFlavor(workload.size) if workload.size in k8s_sizes else VDC_SIZE.K8SNodeFlavor.SMALL
            )
            self.kubernetes.append(node)
        elif workload.info.workload_type == WorkloadType.Container:
            if "minio" in workload.flist:
                container = S3Container()
                container.node_id = workload.info.node_id
                container.pool_id = workload.info.pool_id
                container.wid = workload.id
                container.ip_address = workload.network_connection[0].ipaddress
                self.s3.minio = container
            elif "js-sdk" in workload.flist:
                container = VDCThreebot()
                container.node_id = workload.info.node_id
                container.pool_id = workload.info.pool_id
                container.wid = workload.id
                container.ip_address = workload.network_connection[0].ipaddress
                self.threebot = container
        elif workload.info.workload_type == WorkloadType.Zdb:
            zdb = S3ZDB()
            zdb.node_id = workload.info.node_id
            zdb.pool_id = workload.info.pool_id
            zdb.wid = workload.id
            zdb.size = workload.size
            self.s3.zdbs.append(zdb)

    def _get_s3_subdomains(self, subdomain_workloads):
        minio_wid = self.s3.minio.wid
        if not minio_wid:
            return
        for workload in subdomain_workloads:
            if not workload.info.description:
                continue
            try:
                desc = j.data.serializers.json.loads(workload.info.description)
            except Exception as e:
                j.logger.warning(f"failed to load workload {workload.id} description due to error {e}")
                continue
            exposed_wid = desc.get("exposed_wid")
            if exposed_wid == minio_wid:
                self.s3.domain = workload.domain
                self.s3.domain_wid = workload.id

    def _get_threebot_subdomain(self, proxy_workloads):
        # threebot is exposed over gateway
        threebot_wid = self.threebot.wid
        if not threebot_wid:
            return
        non_matching_domains = []
        for workload in proxy_workloads:
            if not workload.info.description:
                continue
            try:
                desc = j.data.serializers.json.loads(workload.info.description)
            except Exception as e:
                j.logger.warning(f"failed to load workload {workload.id} description due to error {e}")
                continue
            exposed_wid = desc.get("exposed_wid")
            if exposed_wid == threebot_wid:
                self.threebot.domain = workload.domain
            else:
                non_matching_domains.append(workload.domain)
        if not self.threebot.domain and non_matching_domains:
            self.threebot.domain = non_matching_domains[-1]

    def apply_grace_period_action(self):
        self.load_info()
        j.logger.info(f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: initialization")
        for k8s in self.kubernetes:
            ip_address = k8s.public_ip
            if ip_address == "::/128":
                continue
            ssh_key = j.clients.sshkey.get(self.vdc_name)
            vdc_key_path = j.core.config.get("VDC_KEY_PATH", "~/.ssh/id_rsa")
            ssh_key.private_key_path = j.sals.fs.expanduser(vdc_key_path)
            ssh_key.load_from_file_system()
            try:
                ssh_client = j.clients.sshclient.get(
                    self.instance_name, user="rancher", host=str(ip_address), sshkey=self.vdc_name
                )
                rc, out, err = ssh_client.sshclient.run("sudo ip link set cni0 down", warn=True)
                if rc:
                    j.logger.critical(
                        f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to shutdown cni0 wid: {k8s.wid}, rc: {rc}, out: {out}, err: {err}"
                    )
                if k8s.role == KubernetesRole.MASTER:
                    rc, out, err = ssh_client.sshclient.run(
                        "sudo iptables -A INPUT -p tcp --destination-port 6443 -j DROP", warn=True
                    )
                    if rc:
                        j.logger.critical(
                            f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to block kubernetes API wid: {k8s.wid}, rc: {rc}, out: {out}, err: {err}"
                        )

                j.clients.sshclient.delete(self.instance_name)
            except Exception as e:
                j.logger.critical(
                    f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to connect to kubernetes controller due to error {str(e)}"
                )
                raise e
        self.is_blocked = True
        self.save()
        j.logger.info(f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: applied successfully")

    def revert_grace_period_action(self):
        self.load_info()
        j.logger.info(f"VDC: {self.solution_uuid}, REVERT_GRACE_PERIOD_ACTION: intializing")
        self.is_blocked = False
        for k8s in self.kubernetes:
            ip_address = k8s.public_ip
            if ip_address == "::/128":
                continue
            ssh_key = j.clients.sshkey.get(self.vdc_name)
            vdc_key_path = j.core.config.get("VDC_KEY_PATH", "~/.ssh/id_rsa")
            ssh_key.private_key_path = j.sals.fs.expanduser(vdc_key_path)
            ssh_key.load_from_file_system()
            try:
                ssh_client = j.clients.sshclient.get(
                    self.instance_name, user="rancher", host=str(ip_address), sshkey=self.vdc_name
                )
                rc, out, err = ssh_client.sshclient.run("sudo ip link set cni0 up", warn=True)
                if rc:
                    j.logger.critical(
                        f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to bring up cni0 wid: {k8s.wid}, rc: {rc}, out: {out}, err: {err}"
                    )
                if k8s.role == KubernetesRole.MASTER:
                    rc, out, err = ssh_client.sshclient.run(
                        "sudo iptables -D INPUT -p tcp --destination-port 6443 -j DROP", warn=True
                    )
                    if rc:
                        j.logger.critical(
                            f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to unblock kubernetes API wid: {k8s.wid}, rc: {rc}, out: {out}, err: {err}"
                        )

                j.clients.sshclient.delete(self.instance_name)
            except Exception as e:
                j.logger.critical(
                    f"VDC: {self.solution_uuid}, GRACE_PERIOD_ACTION: failed to connect to kubernetes controller due to error {str(e)}"
                )
                self.is_blocked = True
                continue

        self.save()
        j.logger.info(f"VDC: {self.solution_uuid}, REVERT_GRACE_PERIOD_ACTION: reverted successfully")

    def show_vdc_payment(self, bot, expiry=5, wallet_name=None):
        discount = FARM_DISCOUNT.get()
        amount = VDC_SIZE.PRICES["plans"][self.flavor] * (1 - discount)

        payment_id, _ = j.sals.billing.submit_payment(
            amount=amount,
            wallet_name=wallet_name or self.prepaid_wallet.instance_name,
            refund_extra=False,
            expiry=expiry,
            description=j.data.serializers.json.dumps(
                {"type": "VDC_INIT", "owner": self.owner_tname, "solution_uuid": self.solution_uuid,}
            ),
        )

        if amount > 0:
            notes = []
            if discount:
                notes = ["For testing purposes, we applied a discount of {:.2f}".format(discount)]
            return j.sals.billing.wait_payment(payment_id, bot=bot, notes=notes), amount, payment_id
        else:
            return True, amount, payment_id

    def show_external_node_payment(self, bot, size, no_nodes=1, expiry=5, wallet_name=None, public_ip=False):
        discount = FARM_DISCOUNT.get()

        if isinstance(size, str):
            size = VDC_SIZE.K8SNodeFlavor[size.upper()]
        amount = VDC_SIZE.PRICES["nodes"][size] * no_nodes
        if public_ip:
            amount += VDC_SIZE.PRICES["services"][VDC_SIZE.Services.IP]

        amount *= 1 - discount

        prepaid_balance = self._get_wallet_balance(self.prepaid_wallet)
        if prepaid_balance >= amount:
            result = bot.single_choice(
                f"Do you want to use your existing balance to pay {amount} TFT? (This will impact the overall expiration of your plan)",
                ["Yes", "No"],
                required=True,
            )
            if result == "Yes":
                amount = 0

        payment_id, _ = j.sals.billing.submit_payment(
            amount=amount,
            wallet_name=wallet_name or self.prepaid_wallet.instance_name,
            refund_extra=False,
            expiry=expiry,
            description=j.data.serializers.json.dumps(
                {"type": "VDC_K8S_EXTEND", "owner": self.owner_tname, "solution_uuid": self.solution_uuid,}
            ),
        )
        if amount > 0:
            notes = []
            if discount:
                notes = ["For testing purposes, we applied a discount of {:.2f}".format(discount)]
            return j.sals.billing.wait_payment(payment_id, bot=bot, notes=notes), amount, payment_id
        else:
            return True, amount, payment_id

    def transfer_to_provisioning_wallet(self, amount, wallet_name=None):
        if not amount:
            return True
        if wallet_name:
            wallet = j.clients.stellar.get(wallet_name)
        else:
            wallet = self.prepaid_wallet
        return self.pay_amount(self.provision_wallet.address, amount, wallet)

    def pay_initialization_fee(self, transaction_hashes, initial_wallet_name, wallet_name=None):
        initial_wallet = j.clients.stellar.get(initial_wallet_name)
        if wallet_name:
            wallet = j.clients.stellar.get(wallet_name)
        else:
            wallet = self.provision_wallet
        # get total amount
        amount = 0
        for t_hash in transaction_hashes:
            effects = initial_wallet.get_transaction_effects(t_hash)
            for effect in effects:
                amount += effect.amount
        amount = round(abs(amount), 6)
        if not amount:
            return True
        return self.pay_amount(initial_wallet.address, amount, wallet)

    def _get_wallet_balance(self, wallet):
        balances = wallet.get_balance().balances
        for b in balances:
            if b.asset_code != "TFT":
                continue
            return float(b.balance)
        return 0

    def pay_amount(self, address, amount, wallet, memo_text=""):
        j.logger.info(f"transfering amount: {amount} from wallet: {wallet.instance_name} to address: {address}")
        deadline = j.data.time.now().timestamp + 5 * 60
        a = wallet.get_asset()
        has_funds = None
        while j.data.time.now().timestamp < deadline:
            if not has_funds:
                try:
                    balances = wallet.get_balance().balances
                    for b in balances:
                        if b.asset_code != "TFT":
                            continue
                        if amount <= float(b.balance) + 0.1:
                            has_funds = True
                            break
                        else:
                            has_funds = False
                            raise j.exceptions.Validation(
                                f"not enough funds in wallet {wallet.instance_name} to pay amount: {amount}. current balance: {b.balance}"
                            )
                except Exception as e:
                    if has_funds is False:
                        j.logger.error(f"not enough funds in wallet {wallet.instance_name} to pay amount: {amount}")
                        raise e
                    j.logger.warning(f"failed to get wallet {wallet.instance_name} balance due to error: {str(e)}")
                    continue

            try:
                return wallet.transfer(address, amount=amount, asset=f"{a.code}:{a.issuer}", memo_text=memo_text)
            except Exception as e:
                j.logger.warning(f"failed to submit payment to stellar due to error {str(e)}")
        j.logger.critical(
            f"failed to submit payment to stellar in time to: {address} amount: {amount} for wallet: {wallet.instance_name}"
        )
        raise j.exceptions.Runtime(
            f"failed to submit payment to stellar in time to: {address} amount: {amount} for wallet: {wallet.instance_name}"
        )

    def get_pools_expiration(self):
        active_pools = self.active_pools
        if not active_pools:
            return 0
        if len(active_pools) < 2:
            return active_pools[0].empty_at
        return min(*[p.empty_at for p in active_pools])

    def get_total_funds(self):
        total_tfts = 0
        for wallet in [self.prepaid_wallet, self.provision_wallet]:
            for balance in wallet.get_balance().balances:
                if balance.asset_code == "TFT":
                    total_tfts += float(balance.balance)
                    break
        return total_tfts

    def get_current_spec(self, load_info=True):
        """
        return
        dict:
            {
                "plan": self.flavor,
                "nodes": [additional_nodes_flavors],
                "services": {
                    "services.IP": count
                }
            }
        """
        if load_info:
            self.load_info()
        result = {"plan": self.flavor, "nodes": [], "services": {VDC_SIZE.Services.IP: 0}}
        no_nodes = VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["no_nodes"]
        node_flavor = VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["size"]
        for k8s in self.kubernetes:
            if k8s.role == KubernetesRole.MASTER:
                continue
            if k8s.size == node_flavor and no_nodes > 0:
                no_nodes -= 1
                continue
            result["nodes"].append(k8s.size)
            if k8s.public_ip != "::/128":
                result["services"][VDC_SIZE.Services.IP] += 1
        return result

    def calculate_spec_price(self):
        current_spec = self.get_current_spec()
        total_price = (
            VDC_SIZE.PRICES["plans"][self.flavor]
            + current_spec["services"][VDC_SIZE.Services.IP] * VDC_SIZE.PRICES["services"][VDC_SIZE.Services.IP]
        )
        for size in current_spec["nodes"]:
            total_price += VDC_SIZE.PRICES["nodes"][size]
        return total_price

    def calculate_funded_period(self, load_info=True):
        """
        return how many days can the vdc be extended with prepaid + provisioning wallet
        """
        if load_info:
            self.load_info()
        total_funds = self.get_total_funds()
        spec_price = self.calculate_spec_price() or 1
        return (total_funds / spec_price) * 30

    def calculate_expiration_value(self, load_info=True):
        funded_period = self.calculate_funded_period(load_info)
        pools_expiration = self.get_pools_expiration()
        return pools_expiration + funded_period * 24 * 60 * 60
