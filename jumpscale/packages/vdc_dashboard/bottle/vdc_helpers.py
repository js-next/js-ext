from bottle import HTTPResponse, abort
from jumpscale.loader import j

from jumpscale.sals.vdc.size import VDC_SIZE
from jumpscale.sals.vdc.models import KubernetesRole

CURRENTVDC = None


def require_vdc_info(fun):
    def inner(*args, **kwargs):
        global CURRENTVDC
        if not CURRENTVDC:
            CURRENTVDC = get_vdc()
        return fun(*args, **kwargs)

    return inner


def get_vdc(load_info=False):
    global CURRENTVDC
    if not j.sals.vdc.list_all():
        abort(500, "Couldn't find any vdcs on this machine, Please make sure to have it configured properly")
    vdc_full_name = list(j.sals.vdc.list_all())[0]
    if not CURRENTVDC or load_info:
        CURRENTVDC = j.sals.vdc.find(vdc_full_name, load_info=load_info)
        CURRENTVDC.save()
    return CURRENTVDC


def _get_addons(flavor, kubernetes_addons):
    """Get all the addons on the basic user plan
    Args:
        flavor(str): user flavor for the plan
        kubernetes_addons(list): all kubernetes nodes
    Returns:
        addons(list): list of addons used by the user over the basic chosen plan
    """
    plan = VDC_SIZE.VDC_FLAVORS.get(flavor)
    plan_nodes_count = plan.get("k8s").get("no_nodes")
    plan_nodes_size = plan.get("k8s").get("size")
    addons = list()
    for addon in kubernetes_addons:
        if addon.role != KubernetesRole.MASTER:
            if addon.size == plan_nodes_size:
                plan_nodes_count -= 1
                if plan_nodes_count < 0:
                    addons.append(addon)
            else:
                addons.append(addon)
    return addons


@require_vdc_info
def _total_capacity():
    addons = _get_addons(CURRENTVDC.flavor, CURRENTVDC.kubernetes)
    plan = VDC_SIZE.VDC_FLAVORS.get(CURRENTVDC.flavor)
    plan_nodes_count = plan.get("k8s").get("no_nodes")
    return plan_nodes_count + len(addons) + 1


@require_vdc_info
def threebot_vdc_helper():
    vdc_dict = CURRENTVDC.to_dict()
    return vdc_dict


@require_vdc_info
def get_expiration_data():
    return_data = {}
    return_data["expiration_days"] = (CURRENTVDC.expiration_date - j.data.time.now()).days
    return_data["expiration_date"] = CURRENTVDC.calculate_expiration_value(False)
    return return_data


@require_vdc_info
def get_wallet_info():
    # Add wallet address
    wallet = CURRENTVDC.prepaid_wallet
    balances = wallet.get_balance()
    balances_data = []
    for item in balances.balances:
        # Add only TFT balance
        if item.asset_code == "TFT":
            balances_data.append(
                {"balance": item.balance, "asset_code": item.asset_code, "asset_issuer": item.asset_issuer}
            )
    return {
        "address": wallet.address,
        "network": wallet.network.value,
        "secret": wallet.secret,
        "balances": balances_data,
    }


@require_vdc_info
def check_plan_autoscalable():
    return len(CURRENTVDC.kubernetes) < _total_capacity(CURRENTVDC)


def _list_alerts(app_name: str = ""):
    return [alert.json for alert in j.tools.alerthandler.find(app_name)]
