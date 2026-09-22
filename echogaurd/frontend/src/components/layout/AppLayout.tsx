import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { NavLink, useNavigate } from 'react-router-dom'
import IncomingCallOverlay from '../ui/IncomingCallOverlay'
import { useIncomingCall } from '../../hooks/useIncomingCall'

export default function AppLayout() {
  const navigate = useNavigate()

const {
  incomingCall,
  acceptCall,
  rejectCall,
} = useIncomingCall()
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="min-h-screen md:ml-64">
        <Topbar />
        <nav className="flex gap-1 overflow-x-auto border-b border-slate-800 bg-slate-950 px-4 py-2 md:hidden" aria-label="Mobile navigation">
          {[
            ['/dashboard', 'Overview'],
            ['/contacts', 'Contacts'],
            ['/threats', 'Threats'],
          ].map(([path, label]) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-lg px-3 py-2 text-sm ${isActive ? 'bg-cyan-500/10 text-cyan-300' : 'text-slate-400'}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
{incomingCall && (
  <IncomingCallOverlay
    call={incomingCall}
    onAccept={() => {
      const callId = acceptCall()

      if (callId) {
        navigate(`/call/${callId}`)
      }
    }}
    onReject={rejectCall}
  />
)}
        <main className="p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}