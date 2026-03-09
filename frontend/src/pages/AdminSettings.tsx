import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listUsers,
  listRoles,
  listProjects,
  listProjectRoles,
  assignProjectRole,
} from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import {
  Shield,
  Users,
  KeyRound,
  Server,
  UserPlus,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';

type TabId = 'users' | 'roles' | 'system' | 'project-roles';

interface UserRecord {
  id: string;
  name: string;
  email: string;
  role?: string;
  is_active: boolean;
}

interface RoleRecord {
  id: string;
  name: string;
  description?: string;
  permissions?: string[];
}

interface ProjectRecord {
  id: string;
  name: string;
  client_name: string;
  status: string;
}

interface ProjectRoleRecord {
  id: string;
  user_id: string;
  role_id: string;
  user_name?: string;
  user_email?: string;
  role_name?: string;
}

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'users', label: 'Users', icon: Users },
  { id: 'roles', label: 'Roles', icon: KeyRound },
  { id: 'system', label: 'System Info', icon: Server },
  { id: 'project-roles', label: 'Project Roles', icon: UserPlus },
];

function UsersSection() {
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => listUsers().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-400">
        <Loader2 size={20} className="animate-spin mr-2" />
        Loading users...
      </div>
    );
  }

  if (!users || users.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        <Users size={40} className="mx-auto mb-3 opacity-50" />
        <p>No users found.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Users</h2>
        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
          {users.length} user{users.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-4 py-3 font-medium text-slate-600">Name</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Role</th>
              <th className="text-left px-4 py-3 font-medium text-slate-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u: UserRecord) => (
              <tr key={u.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-4 py-3 font-medium text-slate-900">{u.name}</td>
                <td className="px-4 py-3 text-slate-500">{u.email}</td>
                <td className="px-4 py-3">
                  {u.role ? (
                    <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                      {u.role}
                    </span>
                  ) : (
                    <span className="text-slate-400">--</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {u.is_active ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle2 size={14} /> Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-slate-400">
                      <XCircle size={14} /> Inactive
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RolesSection() {
  const { data: roles, isLoading } = useQuery({
    queryKey: ['admin-roles'],
    queryFn: () => listRoles().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-400">
        <Loader2 size={20} className="animate-spin mr-2" />
        Loading roles...
      </div>
    );
  }

  if (!roles || roles.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        <KeyRound size={40} className="mx-auto mb-3 opacity-50" />
        <p>No roles configured.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Roles</h2>
        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
          {roles.length} role{roles.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="grid gap-4">
        {roles.map((r: RoleRecord) => (
          <div key={r.id} className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-indigo-50 rounded-lg">
                <KeyRound size={18} className="text-indigo-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900">{r.name}</h3>
                {r.description && (
                  <p className="text-sm text-slate-500 mt-0.5">{r.description}</p>
                )}
                {r.permissions && r.permissions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {r.permissions.map((perm: string) => (
                      <span
                        key={perm}
                        className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono"
                      >
                        {perm}
                      </span>
                    ))}
                  </div>
                )}
                {(!r.permissions || r.permissions.length === 0) && (
                  <p className="text-xs text-slate-400 mt-2">No permissions defined</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SystemInfoSection() {
  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">System Information</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-50 rounded-lg">
              <Server size={18} className="text-green-600" />
            </div>
            <h3 className="font-semibold text-slate-900">Application</h3>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Version</dt>
              <dd className="font-medium text-slate-900">2.0.0</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Environment</dt>
              <dd>
                <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                  {import.meta.env.MODE}
                </span>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Frontend</dt>
              <dd className="font-medium text-slate-900">React + Vite</dd>
            </div>
          </dl>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-50 rounded-lg">
              <Shield size={18} className="text-purple-600" />
            </div>
            <h3 className="font-semibold text-slate-900">API Configuration</h3>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">API Base URL</dt>
              <dd className="font-medium text-slate-900 text-xs font-mono truncate max-w-[200px]">
                {import.meta.env.VITE_API_URL || '/api'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Auth Method</dt>
              <dd className="font-medium text-slate-900">JWT / OAuth2</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">AI Model</dt>
              <dd className="font-medium text-slate-900">GPT-4 / Claude</dd>
            </div>
          </dl>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-amber-50 rounded-lg">
              <CheckCircle2 size={18} className="text-amber-600" />
            </div>
            <h3 className="font-semibold text-slate-900">Status</h3>
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-slate-700">API Server</span>
              <span className="text-green-600 text-xs font-medium ml-auto">Online</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-slate-700">Database</span>
              <span className="text-green-600 text-xs font-medium ml-auto">Connected</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              <span className="text-slate-700">Task Queue</span>
              <span className="text-green-600 text-xs font-medium ml-auto">Running</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProjectRolesSection() {
  const qc = useQueryClient();
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [assignUserId, setAssignUserId] = useState('');
  const [assignRoleId, setAssignRoleId] = useState('');

  const { data: projects } = useQuery({
    queryKey: ['admin-projects'],
    queryFn: () => listProjects().then((r) => r.data),
  });

  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => listUsers().then((r) => r.data),
  });

  const { data: roles } = useQuery({
    queryKey: ['admin-roles'],
    queryFn: () => listRoles().then((r) => r.data),
  });

  const { data: projectRoles, isLoading: rolesLoading } = useQuery({
    queryKey: ['project-roles', selectedProjectId],
    queryFn: () => listProjectRoles(selectedProjectId).then((r) => r.data),
    enabled: !!selectedProjectId,
  });

  const assignMut = useMutation({
    mutationFn: () =>
      assignProjectRole(selectedProjectId, {
        user_id: assignUserId,
        role_id: assignRoleId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-roles', selectedProjectId] });
      setAssignUserId('');
      setAssignRoleId('');
    },
  });

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Project Role Assignment</h2>

      {/* Project selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-slate-700 mb-1">Select Project</label>
        <div className="relative">
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="w-full appearance-none border border-slate-300 rounded-lg px-3 py-2 pr-10 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
          >
            <option value="">Choose a project...</option>
            {projects?.map((p: ProjectRecord) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.client_name})
              </option>
            ))}
          </select>
          <ChevronDown
            size={16}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
        </div>
      </div>

      {selectedProjectId && (
        <>
          {/* Current assignments */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Current Assignments</h3>
            {rolesLoading ? (
              <div className="flex items-center text-slate-400 text-sm py-4">
                <Loader2 size={16} className="animate-spin mr-2" />
                Loading assignments...
              </div>
            ) : !projectRoles || projectRoles.length === 0 ? (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-slate-500 text-center">
                No roles assigned to this project yet.
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <th className="text-left px-4 py-3 font-medium text-slate-600">User</th>
                      <th className="text-left px-4 py-3 font-medium text-slate-600">Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {projectRoles.map((pr: ProjectRoleRecord) => (
                      <tr key={pr.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900">
                            {pr.user_name || pr.user_id}
                          </div>
                          {pr.user_email && (
                            <div className="text-xs text-slate-400">{pr.user_email}</div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={pr.role_name || pr.role_id} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Assign new role */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Assign Role</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">User</label>
                <div className="relative">
                  <select
                    value={assignUserId}
                    onChange={(e) => setAssignUserId(e.target.value)}
                    className="w-full appearance-none border border-slate-300 rounded-lg px-3 py-2 pr-10 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                  >
                    <option value="">Select user...</option>
                    {users?.map((u: UserRecord) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.email})
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    size={16}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
                <div className="relative">
                  <select
                    value={assignRoleId}
                    onChange={(e) => setAssignRoleId(e.target.value)}
                    className="w-full appearance-none border border-slate-300 rounded-lg px-3 py-2 pr-10 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
                  >
                    <option value="">Select role...</option>
                    {roles?.map((r: RoleRecord) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    size={16}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                  />
                </div>
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={() => assignMut.mutate()}
                disabled={!assignUserId || !assignRoleId || assignMut.isPending}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {assignMut.isPending ? 'Assigning...' : 'Assign Role'}
              </button>
              {assignMut.isError && (
                <span className="ml-3 text-sm text-red-600">
                  Failed to assign role. Please try again.
                </span>
              )}
              {assignMut.isSuccess && (
                <span className="ml-3 text-sm text-green-600">Role assigned successfully.</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function AdminSettings() {
  const [activeTab, setActiveTab] = useState<TabId>('users');

  return (
    <div className="p-8">
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-100 rounded-lg">
            <Shield size={22} className="text-slate-700" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Admin Settings</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Manage users, roles, and system configuration
            </p>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'users' && <UsersSection />}
      {activeTab === 'roles' && <RolesSection />}
      {activeTab === 'system' && <SystemInfoSection />}
      {activeTab === 'project-roles' && <ProjectRolesSection />}
    </div>
  );
}
