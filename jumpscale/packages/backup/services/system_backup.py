"""
----------------------------------------------------------------------
THE SYSTEM BACKUP SERVICE
----------------------------------------------------------------------
this service will run in the background and execute a backup job for the system paths every hour

Examples:
# ---- run the backup service jobs once manually
JS-NG> j.packages.backup.SystemBackupService().job()

# ---- adding the backup service manually to the servicemanager, although this would done automatically when threebot start
JS-NG> service_manager = j.tools.servicemanager.new('system_backup_service')
JS-NG> service_manager.add_service('system_backup_service', j.sals.fs.expanduser('~/projects/js-sdk//jumpscale/packages/backup/services/system_backup.py'))

# for how to create a backup jobs, check backupjob sal docs
"""

from jumpscale.loader import j
from jumpscale.tools.servicemanager.servicemanager import BackgroundService


class SystemBackupService(BackgroundService):

    BACKUP_JOP_NAME = "systembackupjob"

    # in case the service will create the systemBackupJob
    RESTIC_CLIENT_NAMES = ["systembackupclient"]
    BACKUP_JOP_PATHS = ["~/.config/jumpscale/", "~/sandbox/cfg/"]
    PATHS_TO_EXCLUDE = ["~/.config/jumpscale/logs/*"]

    def __init__(self, interval: 60 * 60, *args, **kwargs):
        super().__init__(interval, *args, **kwargs)

    @classmethod
    def _create_system_backup_job(cls):
        backupjob = j.sals.backupjob.new(
            BACKUP_JOP_NAME, clients=RESTIC_CLIENT_NAMES, paths=BACKUP_JOP_PATHS, paths_to_exclude=PATHS_TO_EXCLUDE
        )

    def job(self):
        """Background backup job to be scheduled.
        """
        if self.BACKUP_JOP_NAME not in j.sals.backupjob.list_all():
            j.logger.warning(
                f"system_backup_service: couldn't get instance of BackupJob with name {self.BACKUP_JOP_NAME}!"
            )
            SystemBackupService._create_system_backup_job()
            j.logger.info(
                f"system_backup_service: {self.BACKUP_JOP_NAME} job successfully created\npaths included: {self.BACKUP_JOP_PATHS}\npaths excluded: {self.PATHS_TO_EXCLUDE}."
            )
        backupjob = j.sals.backupjob.get(self.BACKUP_JOP_NAME)
        backupjob.execute()
        j.logger.info(f"system_backup_service: {self.BACKUP_JOP_NAME} job successfully executed.")


service = SystemBackupService()