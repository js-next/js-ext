import random

from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import deployer
from jumpscale.sals.zos import get as get_zos


class Scheduler:
    def __init__(self, farm_name=None, pool_id=None):
        self.zos = get_zos()
        self._pool_node_ids = None
        if not farm_name and not pool_id:
            raise j.exceptions.Validation("must pass farm_name or pool_id")
        if not farm_name and pool_id:
            pool = self.zos.pools.get(pool_id)
            self._pool_node_ids = pool.node_ids
            farm_id = deployer.get_pool_farm_id(pool_id, pool)
            farm_name = self.zos._explorer.farms.get(farm_id).name
        self.farm_name = farm_name
        self._nodes = []
        self._excluded_node_ids = set()

    def exclude_nodes(self, *node_ids):
        for node_id in node_ids:
            self._excluded_node_ids.add(node_id)

    @property
    def nodes(self):
        if not self._nodes:
            filters = [self.zos.nodes_finder.filter_is_up]
            if self._pool_node_ids:
                filters.append(lambda node: node.node_id in self._pool_node_ids)
            self._nodes = [
                node
                for node in self.zos.nodes_finder.nodes_search(farm_name=self.farm_name)
                if all([f(node) for f in filters])
            ]
        random.shuffle(self._nodes)
        return self._nodes

    def _update_node(self, selected_node, cru=None, mru=None, sru=None, hru=None):
        for node in self._nodes:
            if node.node_id != selected_node.node_id:
                continue
            if cru:
                node.reserved_resources.cru += cru
            if mru:
                node.reserved_resources.mru += mru
            if sru:
                node.reserved_resources.sru += sru
            if hru:
                node.reserved_resources.hru += hru

    def nodes_by_capacity(
        self, cru=None, sru=None, mru=None, hru=None, ip_version=None,
    ):
        """search node with the ability to filter on different criteria

        Args:
          cru: int:  (Default value = None)
          sru: int:  (Default value = None)
          mru: int:  (Default value = None)
          hru: int:  (Default value = None)
          ip_version: str:  (Default value = None)

        yields:
            node
        """
        filters = []
        if ip_version == "IPv4":
            filters.append(self.zos.nodes_finder.filter_public_ip4)
        elif ip_version == "IPv6":
            filters.append(self.zos.nodes_finder.filter_public_ip6)

        for node in self.nodes:
            if node.node_id in self._excluded_node_ids:
                continue
            if not self.check_node_capacity(node.node_id, node, cru, mru, hru, sru):
                continue

            if filters and not all([f(node) for f in filters]):
                continue

            self._update_node(node, cru, mru, hru, sru)
            yield node

    def check_node_capacity(self, node_id, node=None, cru=None, mru=None, hru=None, sru=None):
        if not node:
            for t_node in self.nodes:
                if t_node.node_id == node_id:
                    node = t_node
                    break

        if not node:
            raise j.exceptions.Validation(f"node {node_id} is not part of farm {self.farm_name}")
        total = node.total_resources
        reserved = node.reserved_resources
        if not j.core.config.get("OVER_PROVISIONING"):
            if cru and total.cru - max(0, reserved.cru) < 0:
                return False

            if mru and total.mru - max(0, reserved.mru) < 0:
                return False

            if cru and total.cru - max(0, reserved.cru) < cru:
                return False

            if mru and total.mru - max(0, reserved.mru) < mru:
                return False

        if sru and total.sru - max(0, reserved.sru) < 0:
            return False

        if hru and total.hru - max(0, reserved.hru) < 0:
            return False

        if sru and total.sru - max(0, reserved.sru) < sru:
            return False

        if hru and total.hru - max(0, reserved.hru) < hru:
            return False
        return True

    def refresh_nodes(self, clean_excluded=False):
        self._nodes = []
        if clean_excluded:
            self._excluded_node_ids = set()


class CapacityChecker:
    def __init__(self, farm_name):
        self.farm_name = farm_name
        self.scheduler = Scheduler(farm_name)
        self.result = True

    def exclude_nodes(self, *node_ids):
        self.scheduler.exclude_nodes(*node_ids)

    def add_query(self, cru=None, mru=None, hru=None, sru=None, ip_version=None, no_nodes=1, backup_no=0):
        nodes = []
        for node in self.scheduler.nodes_by_capacity(cru, sru, mru, hru, ip_version):
            nodes.append(node)
            if len(nodes) == no_nodes + backup_no:
                return self.result
        self.result = False
        return self.result

    def refresh(self, clear_excluded=False):
        self.result = True
        self.scheduler.refresh_nodes(clear_excluded)


class GlobalScheduler:
    def __init__(self) -> None:
        self.farm_schedulers = {}

    def get_scheduler(self, farm_name=None, pool_id=None):
        if not farm_name:
            scheduler = Scheduler(farm_name, pool_id)
            farm_name = scheduler.farm_name
            if farm_name not in self.farm_schedulers:
                self.farm_schedulers[farm_name] = scheduler
                return scheduler
        if farm_name in self.farm_schedulers:
            return self.farm_schedulers[farm_name]
        self.farm_schedulers[farm_name] = Scheduler(farm_name, pool_id)
        return self.farm_schedulers[farm_name]

    def add_all_farms(self):
        zos = get_zos()
        for farm in zos._explorer.farms.list():
            self.get_scheduler(farm.name)

    def nodes_by_capacity(
        self, farm_name=None, pool_id=None, cru=None, sru=None, mru=None, hru=None, ip_version=None, all_farms=False
    ):
        my_schedulers = []
        if farm_name or pool_id:
            scheduler = self.get_scheduler(farm_name, pool_id)
            my_schedulers.append(scheduler)
        else:
            if all_farms:
                self.add_all_farms()

            my_schedulers = list(self.farm_schedulers.values())
            random.shuffle(my_schedulers)

        for scheduler in my_schedulers:
            node_generator = scheduler.nodes_by_capacity(cru, sru, mru, hru, ip_version)
            try:
                while True:
                    yield next(node_generator)
            except StopIteration:
                continue
