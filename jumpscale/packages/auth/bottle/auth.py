from functools import wraps
from json import JSONDecodeError
from urllib.parse import urlencode, quote, unquote

import nacl
import requests
from bottle import Bottle, request, abort, redirect, response
from nacl.public import Box
from nacl.signing import VerifyKey

from jumpscale.loader import j

REDIRECT_URL = "https://login.threefold.me"
CALLBACK_URL = "/auth/3bot_callback"
LOGIN_URL = "/auth/login"

app = Bottle()


@app.hook("before_request")
def setup_request():
    request.session = request.environ.get("beaker.session", {})


templates_path = j.sals.fs.join_paths(j.sals.fs.dirname(__file__), "templates")
env = j.tools.jinja2.get_env(templates_path)


@app.route("/login")
def login():
    """List available providers for login and redirect to the selected provider (ThreeFold Connect)

    Returns:
        Renders the template of login page
    """
    session = request.environ.get("beaker.session", {})
    provider = request.query.get("provider")
    next_url = quote(request.query.get("next_url", session.get("next_url", "/")))

    if provider and provider == "3bot":
        state = j.data.idgenerator.chars(20)
        session["next_url"] = next_url
        session["state"] = state
        app_id = request.get_header("host")
        params = {
            "state": state,
            "appid": app_id,
            "scope": j.data.serializers.json.dumps({"user": True, "email": True}),
            "redirecturl": CALLBACK_URL,
            "publickey": j.core.identity.me.nacl.public_key.encode(encoder=nacl.encoding.Base64Encoder),
        }
        params = urlencode(params)
        return redirect(f"{REDIRECT_URL}?{params}", code=302)

    return env.get_template("login.html").render(providers=[], next_url=next_url)


@app.route("/3bot_callback")
def callback():
    """Takes the response from the provider and verify the identity of the logged in user

    Returns:
        Redirect to the wanted page after authentication
    """
    session = request.environ.get("beaker.session")
    data = request.query.get("signedAttempt")

    if not data:
        return abort(400, "signedAttempt parameter is missing")

    data = j.data.serializers.json.loads(data)

    if "signedAttempt" not in data:
        return abort(400, "signedAttempt value is missing")

    username = data["doubleName"]

    if not username:
        return abort(400, "DoubleName is missing")

    res = requests.get(f"https://login.threefold.me/api/users/{username}", {"Content-Type": "application/json"})
    if res.status_code != 200:
        return abort(400, "Error getting user pub key")
    pub_key = res.json()["publicKey"]

    user_pub_key = VerifyKey(j.data.serializers.base64.decode(pub_key))

    # verify data
    signedData = data["signedAttempt"]

    verifiedData = user_pub_key.verify(j.data.serializers.base64.decode(signedData)).decode()

    data = j.data.serializers.json.loads(verifiedData)

    if "doubleName" not in data:
        return abort(400, "Decrypted data does not contain (doubleName)")

    if "signedState" not in data:
        return abort(400, "Decrypted data does not contain (state)")

    if data["doubleName"] != username:
        return abort(400, "username mismatch!")

    # verify state
    state = data["signedState"]
    if state != session["state"]:
        return abort(400, "Invalid state. not matching one in user session")

    nonce = j.data.serializers.base64.decode(data["data"]["nonce"])
    ciphertext = j.data.serializers.base64.decode(data["data"]["ciphertext"])

    try:
        priv = j.core.identity.me.nacl.private_key
        box = Box(priv, user_pub_key.to_curve25519_public_key())
        decrypted = box.decrypt(ciphertext, nonce)
    except nacl.exceptions.CryptoError:
        return abort(400, "Error decrypting data")

    try:
        result = j.data.serializers.json.loads(decrypted)
    except JSONDecodeError:
        return abort(400, "3Bot login returned faulty data")

    if "email" not in result:
        return abort(400, "Email is not present in data")

    email = result["email"]["email"]

    sei = result["email"]["sei"]
    res = requests.post(
        "https://openkyc.live/verification/verify-sei",
        headers={"Content-Type": "application/json"},
        json={"signedEmailIdentifier": sei},
    )

    if res.status_code != 200:
        next_url = request.query.get("next_url", "/auth/logout")
        return env.get_template("email_not_verified.html").render(next_url=next_url)

    username = username.lower()  # workaround usernames that are returned by signed attempt with camel cases
    session["username"] = username
    session["email"] = email
    session["authorized"] = True
    session["signedAttempt"] = signedData
    try:
        tid = j.sals.reservation_chatflow.reservation_chatflow.validate_user({"username": username, "email": email}).id
        session["tid"] = tid
        session["explorer"] = j.core.identity.me.explorer_url
    except Exception as e:
        j.logger.warning(
            f"Error in validating user: {username} with email: {email} in explorer: {j.core.identity.me.explorer_url}\n from {str(e)}"
        )
    return redirect(unquote(session.get("next_url", "/")))


@app.route("/logout")
def logout():
    """Invalidates the user session and redirect to login page

    Returns:
        Redirect to the login page
    """
    session = request.environ.get("beaker.session", {})
    try:
        session.invalidate()
    except AttributeError:
        pass

    next_url = request.query.get("next_url", "/")
    return redirect(f"{LOGIN_URL}?next_url={next_url}")


@app.route("/accessdenied")
def access_denied():
    """Displays the access denied page when the authenticated user is not authorized to view the page

    Returns:
        Renders access denied page
    """
    email = request.environ.get("beaker.session").get("email")
    next_url = request.query.get("next_url", "/auth/logout")
    return env.get_template("access_denied.html").render(email=email, next_url=next_url)


@app.route("/auto_login")
def auto_login():
    """Auto login is used for testing for skipping login and use the current user's info instead.

    Returns:
        Redirect to the admin dashboard.
    """
    if j.core.config.get("AUTO_LOGIN"):
        session = request.environ.get("beaker.session", {})
        session["username"] = request.query.get("username", j.core.identity.me.tname)
        session["email"] = j.core.identity.me.email
        session["authorized"] = True

    return redirect("/admin")


def get_user_info():
    """Parse user information from the session object

    Returns:
        [JSON string]: [user information session]
    """

    def _valid(tname, temail, explorer_url):
        if not j.core.identity.is_configured:
            return False
        if tname != j.core.identity.me.tname:
            return False
        if temail != j.core.identity.me.email:
            return False
        if explorer_url != j.core.identity.me.explorer_url:
            return False
        return True

    session = request.environ.get("beaker.session", {})
    tname = session.get("username", "")
    temail = session.get("email", "")
    tid = session.get("tid", 0)
    explorer_url = session.get("explorer", "")
    # update tid in session when the identity changes
    devmode = not j.core.identity.is_configured

    if not devmode and not _valid(tname, temail, explorer_url):
        session["tid"] = None
        session["explorer"] = j.core.identity.me.explorer_url
        try:
            session["tid"] = j.sals.reservation_chatflow.reservation_chatflow.validate_user(
                {"username": tname, "email": temail}
            ).id
        except Exception as e:
            j.logger.warning(
                f"Error in validating user: {tname} with email: {temail} in explorer: {j.core.identity.me.explorer_url}\n from {str(e)}"
            )
    session.get("signedAttempt", "")
    response.content_type = "application/json"
    return j.data.serializers.json.dumps(
        {
            "username": tname.lower(),
            "email": temail.lower(),
            "tid": tid,
            "devmode": not j.core.config.get_config().get("threebot_connect", True),
        }
    )


def is_admin(tname):
    """Checks if the user provided is considered an admin or not

    Args:
        tname (str): threebot name

    Returns:
        [Bool]: [True if the user is an admin]
    """
    if j.core.identity.is_configured:
        threebot_me = j.core.identity.me
        return threebot_me.tname == tname or tname in threebot_me.admins
    else:
        return True


def authenticated(handler):
    """decorator for the methods to be for authenticated users only

    Args:
        handler (method)
    """

    def decorator(*args, **kwargs):
        session = request.environ.get("beaker.session", {})
        if j.core.config.get_config().get("threebot_connect", True) and j.core.identity.is_configured:
            if not session.get("authorized", False):
                return abort(401)
        return handler(*args, **kwargs)

    return decorator


def admin_only(handler):
    """decorator for methods for admin access only

    Args:
        handler (method)
    """

    def decorator(*args, **kwargs):
        session = request.environ.get("beaker.session")
        if j.core.config.get_config().get("threebot_connect", True):
            username = session.get("username")
            if not is_admin(username):
                return abort(403)

        return handler(*args, **kwargs)

    return decorator


@app.route("/authenticated")
@authenticated
def is_authenticated():
    """get user information if it is authenticated

    Returns:
        [JSON string]: [user information session]
    """
    return get_user_info()


@app.route("/authorized")
@authenticated
@admin_only
def is_authorized():
    """get user information if it is authenticated and authorized as admin only

    Returns:
        [JSON string]: [user information session]
    """
    return get_user_info()


@app.route("/package_authorized/<package_name>")
@authenticated
def is_package_authorized(package_name):
    """
    get user information if it is authorized user in the package config

    Returns:
        [JSON string]: [user information session]
    """
    authorized_users = get_package_admins(package_name)
    user_info = get_user_info()
    user_dict = j.data.serializers.json.loads(user_info)
    username = user_dict["username"]
    # if the package doesn't include admins then allow any authenticated user
    if authorized_users and not any([username in authorized_users, username in j.core.identity.me.admins]):
        return abort(403)
    return user_info


def package_authorized(package_name):
    def decorator(function):
        def wrapper(*args, **kwargs):
            authorized_users = get_package_admins(package_name)
            session = request.environ.get("beaker.session")
            username = session.get("username")
            if authorized_users and not any([username in authorized_users, username in j.core.identity.me.admins]):
                return abort(403)
            return function(*args, **kwargs)

        return wrapper

    return decorator


def login_required(func):
    """Decorator for the methods we want to secure

    Args:
        func (method)
    """

    @wraps(func)
    def decorator(*args, **kwargs):
        session = request.environ.get("beaker.session", {})
        if j.core.config.get_config().get("threebot_connect", True):
            if not session.get("authorized", False):
                session["next_url"] = request.url
                return redirect(LOGIN_URL)
        return func(*args, **kwargs)

    return decorator


def add_package_user(package_name, username):
    package = j.servers.threebot.default.packages.get(package_name)
    if not package:
        raise j.exceptions.Validation(f"can't add admin to non installed package {package_name}")
    package.admins.append(username)
    j.servers.threebot.default.packages.save()


def get_package_admins(package_name):
    package = j.servers.threebot.default.packages.get(package_name)
    if not package:
        raise j.exceptions.Validation(f"package {package_name} is not installed")
    return package.admins
