"""
# Taiga client

## Initialization

Using username and  password:
```
client = j.clients.taiga.new('test', host="https://staging.circles.threefold.me/", username='admin', password='123456')
```
OR using a token

```
client = j.clients.taiga.new('test', host="https://staging.circles.threefold.me/", token='extra secret token string')
```
## Listing

### Listing issues

To get the issues of the user with id 123:
```
client.list_all_issues(123)
```
To get the issues of all users:
```
client.list_all_issues(123)

```
### Listing projects

To list all projects:
```
client.list_all_projects()
```


### Listing milestones

To list all projects:
```
client.list_all_milestones()

```
### Listing user stories

To list the user stories of the user with id 123:

```
client.list_all_user_stories(123)
```

To list the user stories of all users:

```
client.list_all_user_stories()
```


### List team circles

```
client.list_team_circles()
```


### List project circles

```
client.list_project_circles()  ## list_team_circles, list_funnel_circles
```

### List funnel circles

```
client.list_funnel_circles()

```

### Create new circle

if you want full control on the circle creation on priorities, severities, .. etc, you can use `_create_new_circle` method


```
def _create_new_circle(
    self,
    name,
    type_="team",
    description="desc",
    severities=None,
    issues_statuses=None,
    priorities=None,
    issues_types=None,
    user_stories_statuses=None,
    tasks_statuses=None,
    **attrs,
):
```
otherwise you can use `create_new_project_circle,`, `create_new_team_circle`, `create_new_funnel_circle`


### Create new story

```
circle_object.create_story("abc")
```

### Create a new  issue

```
create_issue("my issue")
```

## Exporting

### Export users and circles

```
client.export_as_md("/tmp/taigawiki")
```

### Export users

```
client.export_users_as_md("/tmp/taigawiki")
```
### Export circles
```
client.export_circles_as_md("/tmp/taigawiki")
```
## Operations

### Move a story to a project

```
client.move_story_to_cirlce(789, 123) # story id, project id
```

or using a project object
```
project_object.move_issue(issue_id_or_issue_object, project_id_or_project_object)
```

### Resources urls
All of resources e.g (user, issue, user_story, circle) have `url` property


## Export objects as yaml
to export All objects as yaml all you need is

```
client.export_as_yaml("/tmp/exported_taiga_dir")

```
this will export resources (users, projects, issues, stories, milestones) in `/tmp/exported_taiga_dir/$object_type/$object_id.yaml`
"""

import copy
from collections import defaultdict
from functools import lru_cache
from textwrap import dedent
import threading, time
import dateutil
import dateutil.utils
import gevent
from taiga.models.models import Milestones
import yaml
from jumpscale.clients.base import Client
from jumpscale.clients.taiga.models import (
    Circle,
    CircleIssue,
    CircleStory,
    CircleTask,
    CircleUser,
    FunnelCircle,
    ProjectCircle,
    TeamCircle,
)
from jumpscale.core.base import fields
from jumpscale.loader import j

from taiga import TaigaAPI
from taiga.exceptions import TaigaRestException


class TaigaClient(Client):
    def credential_updated(self, value):
        self._api = None

    host = fields.String(default="https://projects.threefold.me")
    username = fields.String(on_update=credential_updated)
    password = fields.Secret(on_update=credential_updated)
    token = fields.Secret(on_update=credential_updated)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api = None
        self.text = ""

    def __hash__(self):
        return hash(str(self))

    @property
    def api(self):
        if not self._api:
            api = TaigaAPI(host=self.host)
            if self.token:
                api.token = self.token
            else:
                if not self.username or not self.password:
                    raise j.exceptions.Runtime("Token or username and password are required")
                api.auth(self.username, self.password)
            self._api = api
        return self._api

    @lru_cache(maxsize=2048)
    def _get_project(self, project_id):
        return self.api.projects.get(project_id)

    @lru_cache(maxsize=2048)
    def _get_milestone(self, milestone_id):
        if milestone_id:
            return self.api.milestones.get(milestone_id)

    @lru_cache(maxsize=2048)
    def _get_priority(self, priority_id):
        return self.api.priorities.get(priority_id)

    @lru_cache(maxsize=2048)
    def _get_assignee(self, assignee_id):
        return CircleUser(self, self.api.users.get(assignee_id))

    _get_user_by_id = _get_assignee

    def _get_users_by_ids(self, ids=None):
        ids = ids or []
        return [self._get_user_by_id(x) for x in ids]

    def _get_issues_by_ids(self, ids=None):
        ids = ids or []
        return [self._get_issue_by_id(x) for x in ids]

    def _get_task_by_id(self, id):
        return self.api.tasks.get(id)

    @lru_cache(maxsize=2048)
    def _get_issue_status(self, status_id):
        return self.api.issue_statuses.get(status_id)

    @lru_cache(maxsize=2048)
    def _get_user_stories_status(self, status_id):
        return self.api.user_story_statuses.get(status_id)

    @lru_cache(maxsize=2048)
    def _get_task_status(self, status_id):
        return self.api.task_statuses.get(status_id)

    @lru_cache(maxsize=2048)
    def _get_user_id(self, username):
        user = self.api.users.list(username=username)
        if user:
            user = user[0]
            return user.id
        else:
            raise j.exceptions.Input("Couldn't find user with username: {}".format(username))

    @lru_cache(maxsize=2048)
    def _get_user_by_name(self, username):
        theid = self._get_user_id(username)
        return self._get_user_by_id(theid)

    def get_issue_custom_fields(self,id):
        """Get Issue Custom fields

        Args:
            id (int): Issue id

        Returns:
            Array: Array of dictionaries {name: "custom field name", value: {values as dict}}
        """
        issue = self.api.issues.get(id)
        issue_attributes = issue.get_attributes()['attributes_values']
        project_attributes = self._get_project(issue.project).list_issue_attributes()
        custom_fields = []
        for p_attr in project_attributes :
            for k, value in issue_attributes.items():
                if p_attr.id == int(k):
                    custom_fields.append({"name":p_attr.name, "value": yaml.safe_load(value)})
                    break
        
        return custom_fields
    
    def get_story_custom_fields(self,id):
        """Get User_Story Custom fields

        Args:
            id (int): User_Story id

        Returns:
            Array: Array of dictionaries {name: "custom field name", value: {values as dict}}
        """
        user_story = self.api.user_stories.get(id)
        user_story_attributes = user_story.get_attributes()['attributes_values']
        project_attributes = self._get_project(user_story.project).list_user_story_attributes()
        custom_fields = []
        for p_attr in project_attributes :
            for k, value in user_story_attributes.items():
                if p_attr.id == int(k):
                    custom_fields.append({"name":p_attr.name, "value": yaml.safe_load(value)})
                    break
        
        return custom_fields
    
    def get_user_circles(self, username):
        """Get circles owned by user

        Args:
            username (str): Name of the user
        """
        user_id = self._get_user_id(username)
        circles = self.api.projects.list(member=user_id)
        user_circles = []
        for circle in circles:
            if circle.owner["id"] == user_id:
                user_circles.append(self._resolve_object(circle))
        return user_circles

    def get_circles_issues(self, project_id):
        """Get all issues in a circle/project

        Args:
            project_id (int): id of the circle/project

        Raises:
            j.exceptions.NotFound: if couldn't find circle with specified id
        """
        try:
            circle = self.api.projects.get(project_id)
        except TaigaRestException:
            raise j.exceptions.NotFound(f"Couldn't find project with id: {project_id}")

        circle_issues = []
        for issue in circle.list_issues():
            issue.project = self._get_project(issue.project)
            issue.milestone = self._get_milestone(issue.milestone)
            issue.priority = self._get_priority(issue.priority)
            issue.assignee = self._get_assignee(issue.assigned_to)
            issue.status = self._get_issue_status(issue.status)
            circle_issues.append(issue)
        return circle_issues

    def get_user_stories(self, username):
        """Get all stories of a user

        Args:
            username (str): Name of the user
        """
        user_id = self._get_user_id(username)
        user_stories = self.api.user_stories.list(assigned_to=user_id)
        user_stories = []
        for user_story in user_stories:
            # user_story.project = self._get_project(user_story.project)
            # user_story.milestone = self._get_milestone(user_story.milestone)
            user_story.status = self._get_user_stories_status(user_story.status)
            user_stories.append(user_story)
        return user_stories

    def get_user_tasks(self, username):
        """Get all tasks of a user

        Args:
            username (str): Name of the user
        """
        user_id = self._get_user_id(username)
        user_tasks = self.api.tasks.list(assigned_to=user_id)
        user_tasks = []
        for user_task in user_tasks:
            # user_task.project = self._get_project(user_task.project)
            # user_task.milestone = self._get_milestone(user_task.milestone)
            user_task.status = self._get_task_status(user_task.status)
            user_tasks.append(self._resolve_object(user_task))

        return user_tasks

    def move_story_to_circle(self, story_id, project_id):
        """Moves a story to another circle/project

        Args:
            story_id (int): User story id
            project_id (int): circle/project id

        Raises:
            j.exceptions.NotFound: No user story with speicifed id found
            j.exceptions.NotFound: No project with speicifed id found
            j.exceptions.Runtime: [description]

        Returns:
            int: New id of the migrated user story
        """

        def _get_project_status(project_statuses, status):
            for project_status in project_statuses:
                if project_status.name == status:
                    return project_status.id

        try:
            user_story = self.api.user_stories.get(story_id)
        except TaigaRestException:
            raise j.exceptions.NotFound("Couldn't find user story with id: {}".format(story_id))

        project_stories_statuses = self.api.user_story_statuses.list(project=project_id)
        status = self._get_user_stories_status(user_story.status)
        story_status_id = _get_project_status(project_stories_statuses, status)

        try:
            migrate_story = self.api.user_stories.create(
                project=project_id,
                subject=user_story.subject,
                assigned_to=user_story.assigned_to,
                milestone=user_story.milestone,
                status=story_status_id,
                tags=user_story.tags,
            )
        except TaigaRestException:
            raise j.exceptions.NotFound("No project with id: {} found".format(project_id))
        try:
            comments = self.api.history.user_story.get(story_id)
            comments = sorted(comments, key=lambda c: dateutil.parser.isoparse(c["created_at"]))

            for comment in comments:
                migrate_story.add_comment(comment["comment_html"])

            project_tasks_statuses = self.api.task_statuses.list(project=project_id)
            for task in user_story.list_tasks():
                status = self._get_task_status(task.status)
                task_status_id = _get_project_status(project_tasks_statuses, status)
                migrate_task = migrate_story.add_task(
                    subject=task.subject,
                    status=task_status_id,
                    due_date=task.due_date,
                    milestone=task.milestone,
                    assigned_to=task.assigned_to,
                    tags=task.tags,
                    project=migrate_story.project,
                    user_story=migrate_story.id,
                )
                comments = self.api.history.task.get(migrate_task.id)
                comments = sorted(comments, key=lambda c: dateutil.parser.isoparse(c["created_at"]))

                for comment in comments:
                    migrate_task.add_comment(comment["comment_html"])

        except Exception as e:
            self.api.user_stories.delete(migrate_story.id)
            raise j.exceptions.Runtime("Failed to migrate story error was: {}".format(str(e)))

        self.api.user_stories.delete(story_id)
        return migrate_story.id

    def list_all_issues(self, username=""):
        """
        List all issues for specific user if you didn't pass user_id will list all the issues

        Args:
            username (str): username.

        Returns:
            List: List of taiga.models.models.Issue.
        """
        if username:
            user_id = self._get_user_id(username)
            return [CircleIssue(self, self._resolve_object(x)) for x in self.api.issues.list(assigned_to=user_id)]
        else:
            return [CircleIssue(self, self._resolve_object(x)) for x in self.api.issues.list()]

    def list_all_tasks(self, username=""):
        """
        List all tasks for specific user if you didn't pass user_id will list all the tasks

        Args:
            username (str): username.

        Returns:
            List: List of taiga.models.models.Task.
        """
        if username:
            user_id = self._get_user_id(username)
            return [CircleTask(self, self._resolve_object(x)) for x in self.api.tasks.list(assigned_to=user_id)]
        else:
            return [CircleTask(self, self._resolve_object(x)) for x in self.api.tasks.list()]

    def list_all_projects(self):
        """
        List all projects

        Returns:
            List: List of taiga.models.models.Project.
        """
        return [Circle(self, self._resolve_object(x)) for x in self.api.projects.list()]

    def list_all_active_projects(self):
        return [Circle(self, p) for p in self.list_projects_by(lambda x: not x.name.startswith("ARCHIVE_"))]

    def list_all_milestones(self):
        """
        List all milestones

        Returns:
            List: List of taiga.models.models.Milestone.
        """
        return [self._resolve_object(x) for x in self.api.milestones.list()]

    def list_all_user_stories(self, username=""):
        """
        List all user stories for specific user if you didn't pass user_id will list all the available user stories

        Args:
            username (str): username.

        Returns:
            List: List of CircleStory.
        """
        if username:
            user_id = self._get_user_id(username)

            return [CircleStory(self, self._resolve_object(x)) for x in self.api.user_stories.list(assigned_to=user_id)]
        else:
            return [CircleStory(self, self._resolve_object(x)) for x in self.api.user_stories.list()]

    def list_all_users(self):
        """
        List all user stories for specific user if you didn't pass user_id will list all the available user stories

        Args:
            username (str): username.

        Returns:
            List: List of CircleUser.
        """
        circles = self.list_all_projects()
        users = set()
        for c in circles:
            for m in c.members:
                users.add(m)

        return [CircleUser(self, self._get_user_by_id(uid)) for uid in users]

    def get_issue_by_id(self, issue_id):
        """Get issue
        Args:
            issue_id: the id of the desired issue

        Returns:
            Issue object: issue
        """
        return CircleIssue(self, self.api.issues.get(issue_id))

    def _resolve_object(self, obj):
        resolvers = {
            "owners": self._get_users_by_ids,
            "watchers": self._get_users_by_ids,
            "members": self._get_users_by_ids,
            "project": self._get_project,
            "circle": self._get_project,
            "milestone": self._get_milestone,
            "task_status": self._get_task_status,
            "assigned_to": self._get_user_by_id,
            "owner": self._get_user_by_id,
            "issues": self._get_issues_by_ids,
            "tasks": self._get_task_by_id,
        }
        newobj = copy.deepcopy(obj)
        for k in dir(newobj):
            v = getattr(newobj, k)
            if isinstance(v, int) or isinstance(v, list) and v and isinstance(v[0], int):
                if k in resolvers:
                    resolved = None
                    resolver = resolvers[k]
                    try:
                        copied_v = copy.deepcopy(v)
                        resolved = lambda: resolver(copied_v)

                        if isinstance(v, list):
                            setattr(newobj, f"{k}_objects", resolved)
                        else:
                            setattr(newobj, f"{k}_object", resolved)

                    except Exception as e:
                        import traceback

                        traceback.print_exc()

                        j.logger.error(f"error {e}")

        return newobj

    def list_projects_by(self, fn=lambda x: True):
        return [p for p in self.list_all_projects() if fn(p)]

    def list_team_circles(self):
        return [TeamCircle(self, p) for p in self.list_projects_by(lambda x: x.name.startswith("TEAM_"))]

    def list_project_circles(self):
        return [ProjectCircle(self, p) for p in self.list_projects_by(lambda x: x.name.startswith("PROJECT_"))]

    def list_funnel_circles(self):
        return [FunnelCircle(self, p) for p in self.list_projects_by(lambda x: x.name.startswith("FUNNEL_"))]

    def validate_custom_fields(self, attributes):
        """Validate custom fields values to match our requirments

        Args:
            attributes (Array): Output from get_issue/user_story_custom_fields functions

        Raises:
            j.exceptions.Validation: Raise validation exception if any input not valid

        Returns:
            bool: Return True if no exception raised and print logs
        """
        
        for attr in attributes:
            name = attr.get("name")
            value = attr.get("value")
            
            period = value.get("period", "onetime")
            duration = value.get("duration", 1)
            amount = value.get("amount", 0)
            currency = value.get("currency", "eur")
            start_date = value.get("start_date", "{}:{}".format(dateutil.utils.today().month,dateutil.utils.today().year))
            confidence = value.get("confidence", 100)
            user = value.get("user")
            part= value.get("part", "0%")
            type= value.get("type", "revenue")

            if name not in ["bookings", "commission"]:
                raise j.exceptions.Validation('Name: ({}) is unknown custom field, please select one of the following ["bookings", "commission"]'.format(name))

            if period not in ["onetime", "month", "year"]:
                raise j.exceptions.Validation('Period: ({}) not found, please select one of following ["onetime", "month", "year"]'.format(period))

            if duration < 1 or duration > 120:
                raise j.exceptions.Validation('Duration: ({}) is not in range, please select it from 1 to 120'.format(duration))

            if not isinstance(amount, int):
                raise j.exceptions.Validation('Amount: ({}) is not integer, please add int value'.format(amount))

            if currency.replace(" ", "").lower() not in ["usd", "chf", "eur", "gbp", "egp"]:
                raise j.exceptions.Validation('Currency: ({}) is not supported, please use one of the following currencies ["usd", "chf", "eur", "gbp", "egp"]'.format(currency))
            try:
                date = start_date.split(":")
                month = int(date[0])
                year = (
                    int(date[1])
                    if len(date) > 1
                    else dateutil.utils.today().year
                )
                if month < 1 or month > 12:
                    raise j.exceptions.Validation("Please use values from 1 to 12 in Month field, follow format like MONTH:YEAR as 11:2020 or MONTH as 11")
            except ValueError as e:
                raise j.exceptions.Validation("Please use numaric date with the following format MONTH:YEAR as 11:2020 or MONTH as 11")
            except AttributeError as e:
                pass  # Will check what happen if start_date not provide

            if confidence % 10 != 0:
                j.exceptions.Validation("Confidence: ({}) not multiple of 10, it must be multiple of 10".format(confidence))
            
            part_tmp = part.replace('%', '')
            if user != None and user not in self.list_all_users():
                raise j.exceptions.Validation('User: ({}) is not found'.format(user))

            if  int(part_tmp) < 0 or int(part_tmp) > 100:
                j.exceptions.Validation('Part: ({}) is a not a valid percentage, it must be from 0% to 100%')

            if type not in ["revenue", "booking"]:
                raise j.exceptions.Validation('Type: ({}) is not supported type, please choose one of the following ["revenue" , "booking"]'.format(type))

            j.logger.info("Arrtibute: {} passed".format(name))
        
        return True

    def _create_new_circle(
        self,
        name,
        type_="team",
        description="desc",
        severities=None,
        issues_statuses=None,
        priorities=None,
        issues_types=None,
        user_stories_statuses=None,
        tasks_statuses=None,
        custom_fields=None,
        **attrs,
    ):
        severities = severities or ["Low", "Mid", "High"]
        priorities = priorities or ["Wishlist", "Minor", "Normal", "Important", "Critical"]
        issues_statuses = issues_statuses or [
            "New",
            "In progress",
            "Ready for test",
            "Closed",
            "Needs Info",
            "Rejected",
            "Postponed",
        ]
        issues_types = issues_types or []
        user_stories_statuses = user_stories_statuses or []
        tasks_statuses = tasks_statuses or []

        type_ = type_.upper()
        project_name = f"{type_}_{name}"
        p = self.api.projects.create(project_name, description=description)
        for t in tasks_statuses:
            try:
                p.add_task_status(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping task {t} {e}")

        for t in priorities:
            try:
                p.add_priority(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping prio {t} {e}")

        for t in severities:
            try:
                p.add_severity(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping sever {t} {e}")

        for t in issues_statuses:
            try:
                p.add_issue_status(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping status {t} {e}")

        for t in user_stories_statuses:
            try:
                p.add_user_story_status(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping user status {t} {e}")

        for t in issues_types:
            try:
                p.add_issue_type(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping issue type {t} {e}")

        for t in custom_fields:
            try:
                p.add_issue_attribute(t)
                p.add_user_story_attribute(t)
            except Exception as e:
                # check if duplicated
                j.logger.debug(f"skipping custom field type {t} {e}")

        return p

    def create_new_project_circle(
        self, name, description="", **attrs,
    ):
        """Creates a new project circle.

        Args:
            name (str): circle name
            description (str, optional): circle description. Defaults to "".

        Returns:
            [ProjectCircle]: Project circle
        """
        # is a circle starting with name: PROJECT_
        # is structured as kanban
        # its a task management system for managing a project, not people
        # there are no custom fields
        attrs = {
            "is_backlog_activated": False,
            "is_issues_activated": True,
            "is_kanban_activated": True,
            "is_private": False,
            "is_wiki_activated": True,
        }
        issues_types = ["Bug", "Question", "Enhancement"]
        severities = ["Wishlist", "Minor", "Normal", "Important", "Critical"]
        priorities = None

        story_statuses = ["New", "to-start", "in-progress", "Blocked", "Implemented", "Verified", "Archived"]
        item_statuses = ["New", "to-start", "in-progress", "Blocked", "Done"]
        issues_statuses = ["New", "to-start", "in-progress", "Blocked", "Implemented", "Closed", "Rejected", "Postponed", "Archived"]

        return ProjectCircle(self,
            self._create_new_circle(
                name,
                type_="project",
                description=description,
                severities=severities,
                issues_statuses=issues_statuses,
                priorities=priorities,
                issues_types=issues_types,
                user_stories_statuses=story_statuses,
                tasks_statuses=item_statuses,
                **attrs,
            ),
        )

    def create_new_team_circle(self, name, description="", **attrs):
        """Creates a new team circle. using sprints & timeline (does not use kanban)

        Args:
            name (str): circle name
            description (str, optional): circle description. Defaults to "".
            severities (List[str], optional): list of strings to represent severities. Defaults to None.
            issues_statuses (List[str], optional): list of strings to represent issues_stauses. Defaults to None.
            priorities (List[str], optional): list of strings to represent priorities. Defaults to None.
            issues_types (List[str], optional): list of strings to represent issues types. Defaults to None.
            user_stories_statuses (List[str], optional): list of strings to represent user stories. Defaults to None.
            tasks_statuses (List[str], optional): list of strings to represent task statuses. Defaults to None.

        Returns:
            [TeamCircle]: team circle
        """

        # starts with TEAM_ ...
        # represents a group of people working together on aligned journey
        # is using sprints & timeline (does not use kanban)
        # no custom fields
        # see the TEMPLATE_TEAM as example on circles.threefold.me
        attrs = {
            "is_backlog_activated": True,
            "is_issues_activated": True,
            "is_kanban_activated": False,
            "is_private": False,
            "is_wiki_activated": True,
        }
        issues_types = ["Bug", "Question", "Enhancement"]
        severities = ["Wishlist", "Minor", "Normal", "Important", "Critical"]
        priorities = None

        story_statuses = ["New", "to-start", "in-progress", "Blocked", "Implemented", "Verified", "Archived"]
        item_statuses = ["New", "to-start", "in-progress", "Blocked", "Done"]
        issues_statuses = ["New", "to-start", "in-progress", "Blocked", "Implemented", "Closed", "Rejected", "Postponed", "Archived"]

        return TeamCircle(
            self,
            self._create_new_circle(
                name,
                type_="team",
                description=description,
                severities=severities,
                issues_statuses=issues_statuses,
                priorities=priorities,
                issues_types=issues_types,
                user_stories_statuses=story_statuses,
                tasks_statuses=item_statuses,
                **attrs,
            ),
        )

    def create_new_funnel_circle(self, name, description="", **attrs):
        """Creates a new funnel circle. using sprints & timeline (does not use kanban)

        Args:
            name (str): circle name
            description (str, optional): circle description. Defaults to "".

        Returns:
            [FunnelCircle]: funnel circle
        """
        attrs = {
            "is_backlog_activated": False,
            "is_issues_activated": True,
            "is_kanban_activated": True,
            "is_private": False,
            "is_wiki_activated": True,
        }

        # #issue
        # New
        # Interested
        # Deal (means moved to story)
        # Blocked / Need Info (something to be done to ublock)
        # Lost
        # Postponed
        # Won
        # # story (is a deal)
        # New (means is a deal, we need to make a proposal, or customer said yes so we can continue)
        # Proposal
        # Contract
        # Blocked / Need Info (something to be done to ublock)
        # Project (once project, will go out of funnel and will be dealt with as a PROJECT_ ...) = closed
        # # item (is a task or checklist on the story)
        # New
        # In progress
        # Verification
        # Closed
        # Needs info

        severities = ["unknown", "low", "25%", "50%", "75%", "90%"]
        priorities = ["Low", "Normal", "High"]
        issues_types = "oportunity"

        issues_statuses = ["New", "Interested", "Deal", "Blocked", "NeedInfo", "Lost", "Postponed", "Won",]
        story_statuses = ["New", "Proposal", "Contract", "Blocked", "NeedInfo", "Closed"]
        task_statuses = ["New", "In progress", "Verification", "Needs info", "Closed"]
        
        custom_fields = ["bookings", "commission"]

        return FunnelCircle(
            self,
            self._create_new_circle(
                name,
                type_="funnel",
                description=description,
                severities=severities,
                issues_statuses=issues_statuses,
                priorities=priorities,
                issues_types=issues_types,
                user_stories_statuses=story_statuses,
                tasks_statuses=task_statuses,
                custom_fields=custom_fields,
                **attrs,
            ),
        )

    def export_circles_as_md(self, wikipath="/tmp/taigawiki", modified_only=True):
        """export circles into {wikipath}/src/circles

        Args:
            wikipath (str, optional): wiki path. Defaults to "/tmp/taigawiki".
        """
        path = j.sals.fs.join_paths(wikipath, "src", "circles")

        j.sals.fs.mkdirs(path)
        circles = self.list_all_active_projects()

        def write_md_for_circle(circle):
            circle_md = circle.as_md
            circle_mdpath = j.sals.fs.join_paths(path, f"{circle.clean_name}.md")
            if not (modified_only and j.sals.fs.exists(circle_mdpath) and j.sals.fs.read_ascii(circle_mdpath)  == circle_md):
                j.sals.fs.write_ascii(circle_mdpath, circle_md)

        circles_mdpath = j.sals.fs.join_paths(path, "circles.md")
        circles_mdcontent = "# circles\n\n"
        for c in circles:
            circles_mdcontent += f"[{c.name}](./{c.clean_name}.md)\n"

        j.sals.fs.write_ascii(circles_mdpath, circles_mdcontent)

        greenlets = [gevent.spawn(write_md_for_circle, gcircle_obj) for gcircle_obj in circles]
        gevent.joinall(greenlets)

    def export_users_as_md(self, wikipath="/tmp/taigawiki", modified_only=True):
        """export users into {wikipath}/src/users

        Args:
            wikipath (str, optional): wiki path. Defaults to "/tmp/taigawiki".
        """

        path = j.sals.fs.join_paths(wikipath, "src", "users")
        j.sals.fs.mkdirs(path)
        users_objects = self.list_all_users()

        users_mdpath = j.sals.fs.join_paths(path, "users.md")
        users_mdcontent = "# users\n\n"

        def write_md_for_user(user):
            user_md = user.as_md
            user_mdpath = j.sals.fs.join_paths(path, f"{user.clean_name}.md")
            if not (modified_only and j.sals.fs.exists(user_mdpath) and j.sals.fs.read_ascii(user_mdpath) == user_md):
                j.sals.fs.write_ascii(user_mdpath, user_md)

        for u in users_objects:
            users_mdcontent += f"[{u.username}](./{u.clean_name}.md)\n"

        j.sals.fs.write_ascii(users_mdpath, users_mdcontent)

        greenlets = [gevent.spawn(write_md_for_user, guser_obj) for guser_obj in users_objects]
        gevent.joinall(greenlets)

    def export_as_md(self, wiki_path="/tmp/taigawiki", modified_only=True):
        """export taiga instance into a wiki  showing users and circles

        Args:
            wiki_src_path (str, optional): wiki path. Defaults to "/tmp/taigawiki".
        """
        gs = []
        gs.append(gevent.spawn(self.export_circles_as_md, wiki_path, modified_only))
        gs.append(gevent.spawn(self.export_users_as_md, wiki_path, modified_only))
        gevent.joinall(gs)
        readme_md_path = j.sals.fs.join_paths(wiki_path, "src", "readme.md")
        content = dedent(
            f"""
            # Taiga overview

            - [circles](./circles/circles.md)
            - [usuers](./users/users.md)
        """
        )
        j.sals.fs.write_ascii(readme_md_path, content)

    def export_as_md_five_min(self, wiki_path="/tmp/taigawiki", modified_only=True):
        FIVE_MIN = 0
        repeater = threading.Event()
        while not repeater.wait(FIVE_MIN):
            FIVE_MIN = 300
            self.export_as_md(wiki_path,modified_only)

    def export_as_yaml(self, export_dir="/tmp/export_dir"):
        def _export_objects_to_dir(objects_dir, objects_fun):
            j.sals.fs.mkdirs(objects_dir)
            try:
                objects = objects_fun()
                for obj in objects:
                    outpath = j.sals.fs.join_paths(objects_dir, f"{obj.id}.yaml")
                    with open(outpath, "w") as f:
                        yaml.dump(obj.to_dict(), f)
            except Exception as e:
                import  traceback
                traceback.print_exc()
                j.logger.error(e)

        projects_path = j.sals.fs.join_paths(export_dir, "projects")
        stories_path = j.sals.fs.join_paths(export_dir, "stories")
        issues_path = j.sals.fs.join_paths(export_dir, "issues")
        tasks_path = j.sals.fs.join_paths(export_dir, "tasks")
        milestones_path = j.sals.fs.join_paths(export_dir, "milestones")
        users_path = j.sals.fs.join_paths(export_dir, "users")
        def on_err(*args,  **kwargs):
            print("err, ", args, kwargs)

        
        gs = []
        gs.append(gevent.spawn(_export_objects_to_dir, projects_path, self.list_all_active_projects))
        gs.append(gevent.spawn(_export_objects_to_dir, stories_path, self.list_all_user_stories))
        for g in gs:
            g.link_exception(on_err)
        gevent.joinall(gs)
        gs =[]
        
        gs.append(gevent.spawn(_export_objects_to_dir, issues_path, self.list_all_issues))
        gs.append(gevent.spawn(_export_objects_to_dir, milestones_path, self.list_all_milestones))
        for g in gs:
            g.link_exception(on_err)
        gevent.joinall(gs)
        gs  =[]
        
        gs.append(gevent.spawn(_export_objects_to_dir, users_path, self.list_all_users))
        gs.append(gevent.spawn(_export_objects_to_dir, tasks_path, self.list_all_tasks))
        for g in gs:
            g.link_exception(on_err)
        gevent.joinall(gs)

    def _import_project(self, projects_path, file):
        if file.endswith(".yaml") or file.endswith(".yml"):
            with open(j.sals.fs.join_paths(projects_path, file)) as f:
                project_obj = yaml.full_load(f)
                circle_proj = None
                # Funnel Circle
                if project_obj['name'].lower() == "funnel":
                    circle_proj = self.create_new_funnel_circle(project_obj['name'], project_obj['description'])
                # Team Circle
                elif project_obj['name'].lower() == "team":
                    circle_proj = self.create_new_team_circle(project_obj['name'], project_obj['description'])
                # Project Circle
                elif project_obj['name'].lower() == "project":
                    circle_proj = self.create_new_project_circle(project_obj['name'], project_obj['description'])
                # Any Other Circle  
                else:
                    circle_proj = self._create_new_circle(project_obj['name'], project_obj['description'])
                    circle_proj.is_backlog_activated = project_obj['is_backlog_activated']
                    circle_proj.is_issues_activated = project_obj['is_issues_activated']
                    circle_proj.is_kanban_activated = project_obj['is_kanban_activated']
                    circle_proj.is_wiki_activated = project_obj['is_wiki_activated']
                    
                circle_proj.is_private = project_obj['is_private']
                circle_proj.videoconferences = project_obj['videoconferences']
                circle_proj.total_milestones = project_obj['total_milestones']
                circle_proj.total_story_points = project_obj['total_story_points']

    def import_from_yaml(self, import_dir="/tmp/export_dir"):
        # Folders
        projects_path = j.sals.fs.join_paths(import_dir, "projects")
        stories_path = j.sals.fs.join_paths(import_dir, "stories")
        issues_path = j.sals.fs.join_paths(import_dir, "issues")
        tasks_path = j.sals.fs.join_paths(import_dir, "tasks")
        milestones_path = j.sals.fs.join_paths(import_dir, "milestones")
        users_path = j.sals.fs.join_paths(import_dir, "users")
        
        # List of Files inside each Folder
        projects =  j.sals.fs.os.listdir(projects_path)
        stories =  j.sals.fs.os.listdir(stories_path)
        issues =  j.sals.fs.os.listdir(issues_path)
        tasks =  j.sals.fs.os.listdir(tasks_path)
        milestones =  j.sals.fs.os.listdir(milestones_path)
        users =  j.sals.fs.os.listdir(users_path)
        
        
        gs = []
        gs.append(gevent.spawn(self._import_project, projects_path, file) for file in projects)
