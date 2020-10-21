from beaker.middleware import SessionMiddleware
from bottle import Bottle, request, HTTPResponse
from jumpscale.clients.explorer.models import NextAction, WorkloadType
from jumpscale.packages.threebot_deployer.bottle.utils import (
    list_threebot_solutions,
    stop_threebot_solution,
    delete_threebot_solution,
)

from jumpscale.loader import j
from jumpscale.packages.auth.bottle.auth import SESSION_OPTS, login_required, get_user_info
from jumpscale.packages.marketplace.bottle.models import UserEntry
from jumpscale.core.base import StoredFactory
from jumpscale.packages.threebot_deployer.actors.backup import Backup

app = Bottle()


@app.route("/api/threebots/list")
@login_required
def list_threebots() -> str:
    solutions = []
    user_info = j.data.serializers.json.loads(get_user_info())
    solutions = j.sals.marketplace.solutions.list_solutions(user_info["username"], "threebot")
    return j.data.serializers.json.dumps({"data": solutions})


@app.route("/api/threebots/list-all")
@login_required
def list_threebots() -> str:
    user_info = j.data.serializers.json.loads(get_user_info())
    threebots = list_threebot_solutions(user_info["username"])
    return j.data.serializers.json.dumps({"data": threebots})


@app.route("/api/threebots/stop")
@login_required
def stop_threebot() -> str:
    data = j.data.serializers.json.loads(request.body.read())
    user_info = j.data.serializers.json.loads(get_user_info())
    threebot = stop_threebot_solution(owner=user_info["username"], solution_uuid=data.get("uuid"))

    return j.data.serializers.json.dumps({"data": threebot})


@app.route("/api/solutions/cancel", method="POST")
@login_required
def cancel_solution():
    user_info = j.data.serializers.json.loads(get_user_info())
    data = j.data.serializers.json.loads(request.body.read())
    j.sals.marketplace.solutions.cancel_solution(user_info["username"], data["wids"], delete_pool=True)
    return j.data.serializers.json.dumps({"result": True})


@app.route("/api/allowed", method="GET")
@login_required
def allowed():
    user_factory = StoredFactory(UserEntry)
    user_info = j.data.serializers.json.loads(get_user_info())
    tname = user_info["username"]
    explorer_url = j.core.identity.me.explorer.url
    instances = user_factory.list_all()
    for name in instances:
        user_entry = user_factory.get(name)
        if user_entry.tname == tname and user_entry.explorer_url == explorer_url and user_entry.has_agreed:
            return j.data.serializers.json.dumps({"allowed": True})
    return j.data.serializers.json.dumps({"allowed": False})


@app.route("/api/accept", method="GET")
@login_required
def accept():
    user_factory = StoredFactory(UserEntry)

    user_info = j.data.serializers.json.loads(get_user_info())
    tname = user_info["username"]
    explorer_url = j.core.identity.me.explorer.url

    if "testnet" in explorer_url:
        explorer_name = "testnet"
    elif "devnet" in explorer_url:
        explorer_name = "devnet"
    elif "explorer.grid.tf" in explorer_url:
        explorer_name = "mainnet"
    else:
        return HTTPResponse(
            j.data.serializers.json.dumps({"error": f"explorer {explorer_url} is not supported"}),
            status=500,
            headers={"Content-Type": "application/json"},
        )

    user_entry = user_factory.get(f"{explorer_name}_{tname.replace('.3bot', '')}")
    if user_entry.has_agreed:
        return HTTPResponse(
            j.data.serializers.json.dumps({"allowed": True}), status=200, headers={"Content-Type": "application/json"}
        )
    else:
        user_entry.has_agreed = True
        user_entry.explorer_url = explorer_url
        user_entry.tname = tname
        user_entry.save()
        return HTTPResponse(
            j.data.serializers.json.dumps({"allowed": True}), status=201, headers={"Content-Type": "application/json"}
        )


app = SessionMiddleware(app, SESSION_OPTS)
