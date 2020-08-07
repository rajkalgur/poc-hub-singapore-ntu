import os
import string
import escapism

# Enable JupyterLab interface if enabled.

if os.environ.get('JUPYTERHUB_ENABLE_LAB', 'false').lower() in ['true', 'yes', 'y', '1']:
    c.Spawner.environment = dict(JUPYTER_ENABLE_LAB='true')

# Setup location for customised template files.

c.JupyterHub.template_paths = ['/opt/app-root/src/templates']

# Setup configuration for authenticating using LDAP. In this case we
# need to deal with separate LDAP servers based on the domain name so
# we need to provide a custom authenticator which can delegate to the
# respective LDAP authenticator instance for the domain.

from ldapauthenticator import LDAPAuthenticator

c.LDAPAuthenticator.use_ssl = True
c.LDAPAuthenticator.lookup_dn = True
c.LDAPAuthenticator.lookup_dn_search_filter = '({login_attr}={login})'
c.LDAPAuthenticator.escape_userdn = False
c.LDAPAuthenticator.valid_username_regex = '^[A-Za-z0-9\\\._-]{7,}$'
c.LDAPAuthenticator.user_attribute = 'sAMAccountName'
c.LDAPAuthenticator.lookup_dn_user_dn_attribute = 'sAMAccountName'
c.LDAPAuthenticator.escape_userdn = False

c.LDAPAuthenticator.lookup_dn_search_user = os.environ['LDAP_SEARCH_USER']
c.LDAPAuthenticator.lookup_dn_search_password = os.environ['LDAP_SEARCH_PASSWORD']

tmw_authenticator = LDAPAuthenticator()
tmw_authenticator.server_address = 'tmw.com'
tmw_authenticator.bind_dn_template = ['tmw\\{username}']
tmw_authenticator.user_search_base = 'DC=tmw'

from jupyterhub.auth import Authenticator

class MultiLDAPAuthenticator(Authenticator):

    def authenticate(self, handler, data):
        domain = data['domain'].lower()

        data['username'] = data['username'].lower()

        if domain == 'tmw':
            return tmw_authenticator.authenticate(handler, data)        

        self.log.warn('domain:%s Unknown authentication domain name', domain)
        return None

c.JupyterHub.authenticator_class = MultiLDAPAuthenticator

if os.path.exists('/opt/app-root/configs/admin_users.txt'):
    with open('/opt/app-root/configs/admin_users.txt') as fp:
        content = fp.read().strip()
        if content:
            c.Authenticator.admin_users = set(content.split())

if os.path.exists('/opt/app-root/configs/user_whitelist.txt'):
    with open('/opt/app-root/configs/user_whitelist.txt') as fp:
        c.Authenticator.whitelist = set(fp.read().strip().split())

rest_api_password = os.environ.get('REST_API_PASSWORD')

if rest_api_password:
    c.JupyterHub.service_tokens = {
        rest_api_password: 'jupyterhub-rest-api-user'
    }

# Provide persistent storage for users notebooks. We share one
# persistent volume for all users, mounting just their subdirectory into
# their pod. The persistent volume type needs to be ReadWriteMany so it
# can be mounted on multiple nodes as can't control where pods for a
# user may land. Because it is a shared volume, there are no quota
# restrictions which prevent a specific user filling up the entire
# persistent volume.

volume_version_number = os.environ.get('VOLUME_VERSION_NUMBER', '')

c.KubeSpawner.user_storage_pvc_ensure = False
c.KubeSpawner.pvc_name_template = '%s-notebooks-pvc%s' % (
        c.KubeSpawner.hub_connect_ip, volume_version_number)

c.KubeSpawner.volumes = [
    {
        'name': 'notebooks',
        'persistentVolumeClaim': {
            'claimName': c.KubeSpawner.pvc_name_template
        }
    }
]

volume_mounts_user = [
    {
        'name': 'notebooks',
        'mountPath': '/opt/app-root/src',
        'subPath': 'users/{username}'
    }
]

volume_mounts_admin = [
    {
        'name': 'notebooks',
        'mountPath': '/opt/app-root/src/users',
        'subPath': 'users'
    }
]

def interpolate_properties(spawner, template):
    safe_chars = set(string.ascii_lowercase + string.digits)
    username = escapism.escape(spawner.user.name, safe=safe_chars,
            escape_char='-').lower()

    return template.format(
        userid=spawner.user.id,
        username=username)

def expand_strings(spawner, src):
    if isinstance(src, list):
        return [expand_strings(spawner, i) for i in src]
    elif isinstance(src, dict):
        return {k: expand_strings(spawner, v) for k, v in src.items()}
    elif isinstance(src, str):
        return interpolate_properties(spawner, src)
    else:
        return src

def modify_pod_hook(spawner, pod):
    if spawner.user.admin:
        volume_mounts = volume_mounts_admin
        workspace = interpolate_properties(spawner, 'users/{username}/workspace')
    else:
        volume_mounts = volume_mounts_user
        workspace = 'workspace'

    os.makedirs(interpolate_properties(spawner,
            '/opt/app-root/notebooks/users/{username}'), exist_ok=True)

    pod.spec.containers[0].env.append(dict(name='JUPYTER_MASTER_FILES',
            value='/opt/app-root/master'))
    pod.spec.containers[0].env.append(dict(name='JUPYTER_WORKSPACE_NAME',
            value=workspace))
    pod.spec.containers[0].env.append(dict(name='JUPYTER_SYNC_VOLUME',
            value='true'))

    pod.spec.containers[0].volume_mounts.extend(
            expand_strings(spawner, volume_mounts))

    return pod

c.KubeSpawner.modify_pod_hook = modify_pod_hook

# Setup resource limits for memory and CPU.

cpu_request = os.environ.get('NOTEBOOK_CPU_REQUEST')
cpu_limit = os.environ.get('NOTEBOOK_CPU_LIMIT')

if cpu_request:
    c.Spawner.cpu_guarantee = float(cpu_request)

if cpu_limit:
    c.Spawner.cpu_limit = float(cpu_limit)

memory_request = os.environ.get('NOTEBOOK_MEMORY_REQUEST')
memory_limit = os.environ.get('NOTEBOOK_MEMORY_LIMIT')

if memory_request:
    c.Spawner.mem_guarantee = convert_size_to_bytes(memory_request)

if memory_limit:
    c.Spawner.mem_limit = convert_size_to_bytes(memory_limit)

# Setup services for backups and idle notebook culling.

jupyterhub_service_name = os.environ.get('JUPYTERHUB_SERVICE_NAME', 'jupyterhub')

c.JupyterHub.services = [
    {
        'name': 'jupyterhub-rest-api-user',
        'admin': True,
    },
    {
        'name': 'backup-users',
        'admin': True,
        'command': ['backup-user-details',
                '--backups=/opt/app-root/notebooks/backups',
                '--config-map=%s-cfg-backup' % jupyterhub_service_name]
    }
]

idle_timeout = os.environ.get('JUPYTERHUB_IDLE_TIMEOUT')

if idle_timeout and int(idle_timeout):
    c.JupyterHub.services.extend([
        {
            'name': 'cull-idle',
            'admin': True,
            'command': ['cull-idle-servers', '--timeout=%s' % idle_timeout]
        }
    ])
