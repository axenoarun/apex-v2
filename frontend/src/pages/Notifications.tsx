import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNotifications, markNotificationRead, markAllRead } from '../api/endpoints';
import { Bell, CheckCheck } from 'lucide-react';

export default function Notifications() {
  const qc = useQueryClient();

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications().then((r) => r.data),
  });

  const markReadMut = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const markAllMut = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['unread-count'] });
    },
  });

  const unreadCount = notifications?.filter((n: any) => !n.read).length || 0;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-slate-700" />
          <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5">{unreadCount} unread</span>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllMut.mutate()}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700"
          >
            <CheckCheck size={16} /> Mark all read
          </button>
        )}
      </div>

      {isLoading && <div className="text-slate-500 text-sm">Loading notifications...</div>}

      <div className="space-y-2">
        {notifications?.map((n: any) => (
          <div
            key={n.id}
            className={`bg-white rounded-xl border p-4 flex items-start justify-between ${
              n.read ? 'border-slate-200' : 'border-blue-200 bg-blue-50/30'
            }`}
          >
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                  {n.type}
                </span>
                <span className="text-sm font-medium text-slate-800">{n.title}</span>
              </div>
              <p className="text-sm text-slate-600">{n.body}</p>
              <p className="text-xs text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
            </div>
            {!n.read && (
              <button
                onClick={() => markReadMut.mutate(n.id)}
                className="text-xs text-blue-600 hover:text-blue-700 shrink-0 ml-4"
              >
                Mark read
              </button>
            )}
          </div>
        ))}
        {(!notifications || notifications.length === 0) && !isLoading && (
          <div className="text-center py-12 text-slate-400 text-sm">No notifications yet.</div>
        )}
      </div>
    </div>
  );
}
