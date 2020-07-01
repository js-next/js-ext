from beaker.middleware import SessionMiddleware
from bottle import Bottle, abort, request

from jumpscale.loader import j
from jumpscale.packages.auth.bottle.auth import SESSION_OPTS, login_required, get_user_info
from jumpscale.sals.reservation_chatflow.models import SolutionType

app = Bottle()


@app.route("/api/solutions/<solution_type>")
@login_required
def list_solutions(solution_type: str) -> str:
    solutions = []
    tid = j.data.serializers.json.loads(get_user_info()).get("tid")
    if not tid:
        return abort(400, "User must be registered by explorer, If you register logout aand login again")
    solutions = j.sals.marketplace.deployer.list_solutions(tid, SolutionType[solution_type.title()])
    for solution in solutions:
        solution.pop("reservation_obj", None)
    return j.data.serializers.json.dumps({"data": solutions})


app = SessionMiddleware(app, SESSION_OPTS)
