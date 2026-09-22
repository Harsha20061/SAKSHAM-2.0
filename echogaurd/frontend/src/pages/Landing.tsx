import { ArrowRight, CheckCircle2, PhoneCall, ShieldCheck, ScanSearch } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useTheme } from '../context/ThemeContext'

export default function Landing() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          <Link to="/" className="flex items-center gap-3" aria-label="Saksham 2.0 home">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400 text-slate-950">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <span className="font-semibold tracking-tight">Saksham 2.0</span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-slate-400 md:flex">
            <a href="#how-it-works" className="hover:text-white">How it works</a>
            <a href="#security" className="hover:text-white">Security</a>
            <button type="button" onClick={toggleTheme} className="rounded-lg border border-slate-700 px-3 py-2 hover:border-cyan-400" aria-label="Toggle theme">
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
            <Link to="/login" className="text-white hover:text-cyan-300">Sign in</Link>
          </nav>
          <Link to="/signup" className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300">
            Get started
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-7xl gap-12 px-5 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-8 lg:py-28">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">Secure communication, made clear</p>
            <h1 className="mt-5 max-w-3xl text-5xl font-semibold tracking-tight text-white sm:text-6xl">Trust every voice.</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
              Saksham 2.0 helps you identify suspicious or synthetic voice activity while a call is happening, so important conversations can be handled with confidence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/signup" className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300">
                Start with Saksham <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#how-it-works" className="rounded-lg border border-slate-700 px-5 py-3 font-medium text-slate-200 hover:border-slate-500">See how it works</a>
            </div>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">Live protection</p>
                <p className="mt-1 font-medium text-white">Incoming call analysis</p>
              </div>
              <span className="flex items-center gap-2 text-xs text-emerald-300"><span className="h-2 w-2 rounded-full bg-emerald-400" />Active</span>
            </div>
            <div className="mt-5 space-y-3">
              <PreviewRow icon={<PhoneCall className="h-4 w-4" />} title="Secure call connected" value="00:42" />
              <PreviewRow icon={<ScanSearch className="h-4 w-4" />} title="Voice signal checked" value="Low risk" />
              <PreviewRow icon={<ShieldCheck className="h-4 w-4" />} title="Conversation monitored" value="Protected" />
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-y border-slate-800/80 bg-slate-900/40">
          <div className="mx-auto max-w-7xl px-5 py-16 lg:px-8">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">How it works</p>
            <div className="mt-8 grid gap-4 md:grid-cols-4">
              {['Call', 'Real-time audio', 'Voice analysis', 'Risk assessment'].map((step, index) => (
                <div key={step} className="border-l border-slate-700 pl-4">
                  <p className="text-xs text-slate-500">0{index + 1}</p>
                  <p className="mt-2 font-medium text-white">{step}</p>
                  <p className="mt-2 text-sm text-slate-400">{['Connect with a trusted contact.', 'Listen without changing your call flow.', 'Check voice authenticity and conversation signals.', 'See clear indicators when action is needed.'][index]}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="security" className="mx-auto max-w-7xl px-5 py-16 lg:px-8">
          <div className="grid gap-8 md:grid-cols-3">
            {[
              ['Real-time voice analysis', 'Get useful signal summaries while the conversation is active.'],
              ['Contact-aware calling', 'Keep trusted contacts and security context together.'],
              ['Actionable risk signals', 'Understand when to pause, verify independently, or end a call.'],
            ].map(([title, body]) => (
              <div key={title} className="border-t border-slate-700 pt-5">
                <CheckCircle2 className="h-5 w-5 text-cyan-300" />
                <h2 className="mt-4 font-medium text-white">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-800 px-5 py-6 text-sm text-slate-500">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-3 lg:px-8">
          <span>Saksham 2.0</span>
          <span>Secure communication and voice impersonation protection.</span>
        </div>
      </footer>
    </div>
  )
}

function PreviewRow({ icon, title, value }: { icon: ReactNode; title: string; value: string }) {
  return <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 p-4"><div className="flex items-center gap-3 text-slate-300"><span className="text-cyan-300">{icon}</span>{title}</div><span className="text-sm text-emerald-300">{value}</span></div>
}
