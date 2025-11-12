import { useState, useEffect } from 'react';
import { useAuthToken } from '../utils/auth';

const API_BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : '/api';

interface InvitationRequest {
  id: string;
  email: string;
  name: string | null;
  company: string | null;
  use_case: string | null;
  status: string;
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  rejection_reason: string | null;
  clerk_invitation_id: string | null;
  metadata: Record<string, any> | null;
}

interface InvitationsResponse {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  requests: InvitationRequest[];
}

export function AdminInvitationsPage() {
  const [invitations, setInvitations] = useState<InvitationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('pending');
  const [processingId, setProcessingId] = useState<string | null>(null);
  const { getToken } = useAuthToken();

  const loadInvitations = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
      
      const response = await fetch(`${API_BASE}/admin/invitations?status_filter=${filter}`, {
        headers,
      });
      
      if (!response.ok) {
        throw new Error('Failed to load invitations');
      }
      
      const data = await response.json();
      setInvitations(data);
    } catch (error) {
      console.error('Failed to load invitations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvitations();
  }, [filter]);

  const handleApprove = async (invitationId: string) => {
    if (!confirm('Send invitation to this user?')) return;
    
    setProcessingId(invitationId);
    try {
      const token = await getToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      
      const response = await fetch(`${API_BASE}/admin/invitations/approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ invitation_id: invitationId }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to approve');
      }
      
      await loadInvitations();
    } catch (error: any) {
      alert(`Failed to approve: ${error.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (invitationId: string) => {
    const reason = prompt('Rejection reason (optional):');
    if (reason === null) return;
    
    setProcessingId(invitationId);
    try {
      const token = await getToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      
      const response = await fetch(`${API_BASE}/admin/invitations/reject`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ 
          invitation_id: invitationId,
          reason: reason || undefined 
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to reject');
      }
      
      await loadInvitations();
    } catch (error: any) {
      alert(`Failed to reject: ${error.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Invitation Requests</h1>
        <p className="text-gray-600">Review and approve access requests from users</p>
      </div>

      {/* Stats Cards */}
      {invitations && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-600">Total Requests</div>
            <div className="text-2xl font-bold text-gray-900">{invitations.total}</div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="text-sm text-amber-700">Pending</div>
            <div className="text-2xl font-bold text-amber-900">{invitations.pending}</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-sm text-green-700">Approved</div>
            <div className="text-2xl font-bold text-green-900">{invitations.approved}</div>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-sm text-red-700">Rejected</div>
            <div className="text-2xl font-bold text-red-900">{invitations.rejected}</div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="bg-white border border-gray-200 rounded-lg mb-4">
        <div className="flex border-b border-gray-200">
          {['pending', 'approved', 'rejected'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-6 py-3 font-medium transition-colors ${
                filter === status
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Invitations List */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading...</div>
        ) : !invitations || invitations.requests.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No {filter} invitation requests
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Use Case
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Requested
                  </th>
                  {filter === 'pending' && (
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {invitations.requests.map((request) => (
                  <tr key={request.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{request.email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{request.name || '—'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{request.company || '—'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 max-w-xs truncate">
                        {request.use_case || '—'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{formatDate(request.requested_at)}</div>
                    </td>
                    {filter === 'pending' && (
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleApprove(request.id)}
                          disabled={processingId === request.id}
                          className="text-green-600 hover:text-green-900 mr-4 disabled:opacity-50"
                        >
                          ✓ Approve
                        </button>
                        <button
                          onClick={() => handleReject(request.id)}
                          disabled={processingId === request.id}
                          className="text-red-600 hover:text-red-900 disabled:opacity-50"
                        >
                          ✗ Reject
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
