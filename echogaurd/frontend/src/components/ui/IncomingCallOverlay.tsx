import { Phone, PhoneOff } from 'lucide-react'
import type { CallResponse } from '../../types/calls'

interface IncomingCallOverlayProps {
  call: CallResponse
  onAccept: () => void
  onReject: () => void
}

export default function IncomingCallOverlay({
  onAccept,
  onReject,
}: IncomingCallOverlayProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-8 text-center shadow-2xl">
        <div className="mx-auto flex h-20 w-20 animate-pulse items-center justify-center rounded-full bg-cyan-500/10">
          <Phone className="h-8 w-8 text-cyan-400" />
        </div>

        <h2 className="mt-5 text-2xl font-bold text-white">
          Incoming voice call
        </h2>

        <p className="mt-2 text-slate-400">
          Security protection is ready
        </p>

        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">
            Caller information
          </p>

          <p className="mt-1 text-lg font-semibold text-white">
            Contact details are available after accepting the call.
          </p>
        </div>

        <div className="mt-7 flex justify-center gap-4">
          <button
            type="button"
            onClick={onReject}
            className="flex h-14 w-14 items-center justify-center rounded-full bg-red-600 text-white transition hover:bg-red-500"
            title="Reject call"
          >
            <PhoneOff className="h-6 w-6" />
          </button>

          <button
            type="button"
            onClick={onAccept}
            className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-white transition hover:bg-emerald-500"
            title="Accept call"
          >
            <Phone className="h-6 w-6" />
          </button>
        </div>

        <div className="mt-4 flex justify-center gap-10 text-xs text-slate-500">
          <span>Reject</span>
          <span>Accept</span>
        </div>
      </div>
    </div>
  )
}