import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Check,
  Edit3,
  Loader2,
  Mic,
  MicOff,
  Phone,
  Plus,
  Shield,
  Trash2,
  UserRound,
  X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Modal from '../components/ui/Modal'
import { createCall } from '../services/calls'
import {
  createContact,
  createVoiceProfile,
  deleteContact,
  deleteVoiceProfile,
  getContacts,
  getVoiceProfile,
  searchUsers,
  updateContact,
  updateVoiceProfile,
} from '../services/contacts'
import { getApiErrorMessage } from '../services/errorMessage'
import type {
  Contact,
  UserSearchResult,
  VoiceProfileStatus,
  VoiceProfileStatusResponse,
} from '../types/contacts'

const EMPTY_PROFILE: VoiceProfileStatusResponse = {
  enrolled: false,
  status: 'NOT_ENROLLED',
}

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showAddForm, setShowAddForm] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null)

  const [nickname, setNickname] = useState('')
  const [isTrusted, setIsTrusted] = useState(true)

  const [submitting, setSubmitting] = useState(false)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editNickname, setEditNickname] = useState('')
  const [editTrusted, setEditTrusted] = useState(false)

  const [voiceProfiles, setVoiceProfiles] = useState<Record<string, VoiceProfileStatusResponse>>({})
  const [voiceProfileLoading, setVoiceProfileLoading] = useState<Record<string, boolean>>({})
  const [enrollmentModal, setEnrollmentModal] = useState<{
    contact: Contact
    mode: 'create' | 'update'
  } | null>(null)
  const [consentChecked, setConsentChecked] = useState(false)
  const [recordingState, setRecordingState] = useState<
    'idle' | 'requesting' | 'ready' | 'recording' | 'stopped' | 'uploading' | 'success' | 'error'
  >('idle')
  const [recordingError, setRecordingError] = useState('')
  const [permissionError, setPermissionError] = useState('')
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

  const navigate = useNavigate()
  const streamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const recordingTimerRef = useRef<number | null>(null)
  const audioUrlRef = useRef<string | null>(null)

  const stopRecordingTimer = () => {
    if (recordingTimerRef.current) {
      window.clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }
  }

  const releaseAudioTracks = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
  }

  const resetRecordingSession = () => {
    stopRecordingTimer()
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    chunksRef.current = []
    setAudioBlob(null)
    setRecordingError('')
    setRecordingSeconds(0)
    setRecordingState('ready')
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    setAudioUrl(null)
  }

  const closeEnrollmentModal = () => {
    stopRecordingTimer()
    releaseAudioTracks()
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    mediaRecorderRef.current = null
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    setAudioUrl(null)
    setAudioBlob(null)
    setConsentChecked(false)
    setRecordingError('')
    setPermissionError('')
    setRecordingSeconds(0)
    setRecordingState('idle')
    setEnrollmentModal(null)
  }

  useEffect(() => {
    return () => {
      stopRecordingTimer()
      releaseAudioTracks()
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current)
      }
    }
  }, [])

  const refreshVoiceProfile = useCallback(async (contactId: string): Promise<VoiceProfileStatusResponse> => {
    try {
      const profile = await getVoiceProfile(contactId)
      setVoiceProfiles((current) => ({
        ...current,
        [contactId]: profile,
      }))
      return profile
    } catch {
      const fallback: VoiceProfileStatusResponse = {
        enrolled: false,
        status: 'NOT_ENROLLED',
      }
      setVoiceProfiles((current) => ({
        ...current,
        [contactId]: fallback,
      }))
      return fallback
    }
  }, [])

  const loadContacts = useCallback(async () => {
    try {
      setLoading(true)
      setError('')

      const data = await getContacts()
      setContacts(data)

      await Promise.all(
        data.map(async (contact) => {
          await refreshVoiceProfile(contact.id)
        }),
      )
    } catch (err) {
      console.error(err)
      setError('Unable to load trusted contacts.')
    } finally {
      setLoading(false)
    }
  }, [refreshVoiceProfile])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadContacts()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadContacts])

  async function handleUserSearch(value: string) {
    setSearchQuery(value)
    setSelectedUser(null)

    if (value.trim().length < 2) {
      setSearchResults([])
      return
    }

    try {
      setSearching(true)
      const results = await searchUsers(value.trim())
      setSearchResults(results)
    } catch (err) {
      console.error(err)
      setSearchResults([])
      setError('Unable to search Saksham 2.0 users.')
    } finally {
      setSearching(false)
    }
  }

  function selectUser(user: UserSearchResult) {
    setSelectedUser(user)
    setSearchQuery(user.username)
    setSearchResults([])
    setError('')
  }

  function resetAddForm() {
    setSearchQuery('')
    setSearchResults([])
    setSelectedUser(null)
    setNickname('')
    setIsTrusted(true)
    setShowAddForm(false)
    setError('')
  }

  async function handleAddContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedUser) {
      setError('Please search for and select a user first.')
      return
    }

    if (!nickname.trim()) {
      setError('Please enter a nickname.')
      return
    }

    try {
      setSubmitting(true)
      setError('')

      await createContact({
        contact_user_id: selectedUser.id,
        nickname: nickname.trim(),
        is_trusted: isTrusted,
      })

      resetAddForm()
      await loadContacts()
    } catch (err: unknown) {
      console.error(err)
      setError(getApiErrorMessage(err, 'Unable to add contact.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleCall = async (userId: string) => {
    try {
      const call = await createCall({
        receiver_id: userId,
      })
      navigate(`/call/${call.id}`)
    } catch (error) {
      console.error('Failed to create call:', error)
    }
  }

  function startEditing(contact: Contact) {
    setEditingId(contact.id)
    setEditNickname(contact.nickname)
    setEditTrusted(contact.is_trusted)
  }

  function cancelEditing() {
    setEditingId(null)
    setEditNickname('')
    setEditTrusted(false)
  }

  async function handleUpdate(contactId: string) {
    if (!editNickname.trim()) {
      setError('Nickname cannot be empty.')
      return
    }

    try {
      setSubmitting(true)
      setError('')

      await updateContact(contactId, {
        nickname: editNickname.trim(),
        is_trusted: editTrusted,
      })

      cancelEditing()
      await loadContacts()
    } catch (err: unknown) {
      console.error(err)
      setError(getApiErrorMessage(err, 'Unable to update contact.'))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(contactId: string) {
    const confirmed = window.confirm('Remove this contact from Saksham 2.0?')
    if (!confirmed) {
      return
    }

    try {
      setError('')
      await deleteContact(contactId)
      await loadContacts()
    } catch (err: unknown) {
      console.error(err)
      setError(getApiErrorMessage(err, 'Unable to delete contact.'))
    }
  }

  async function openEnrollmentModal(contact: Contact, mode: 'create' | 'update') {
    stopRecordingTimer()
    releaseAudioTracks()
    setEnrollmentModal({ contact, mode })
    setConsentChecked(false)
    setRecordingError('')
    setPermissionError('')
    setRecordingSeconds(0)
    setAudioBlob(null)
    setRecordingState('requesting')

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setPermissionError('Microphone access is not supported in this browser.')
      setRecordingState('error')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      setRecordingState('ready')
    } catch {
      setPermissionError('Microphone permission is required.')
      setRecordingState('error')
    }
  }

  async function startRecording() {
    if (!streamRef.current) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        streamRef.current = stream
      } catch {
        setPermissionError('Microphone permission is required.')
        setRecordingState('error')
        return
      }
    }

    if (!MediaRecorder || typeof MediaRecorder === 'undefined') {
      setRecordingError('This browser does not support audio recording.')
      setRecordingState('error')
      return
    }

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : ''

    if (!mimeType) {
      setRecordingError('The current browser does not support a compatible recording format.')
      setRecordingState('error')
      return
    }

    stopRecordingTimer()
    chunksRef.current = []
    setRecordingError('')
    setRecordingState('recording')
    setRecordingSeconds(0)

    const recorder = new MediaRecorder(streamRef.current, { mimeType })
    mediaRecorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data)
      }
    }

    recorder.onstop = () => {
      if (chunksRef.current.length === 0) {
        setRecordingError('Recording failed. Please try again.')
        setRecordingState('error')
        return
      }

      const blob = new Blob(chunksRef.current, { type: mimeType })
      setAudioBlob(blob)
      const nextUrl = URL.createObjectURL(blob)
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current)
      }
      audioUrlRef.current = nextUrl
      setAudioUrl(nextUrl)
      setRecordingState('stopped')
    }

    recorder.start()

    recordingTimerRef.current = window.setInterval(() => {
      setRecordingSeconds((current) => current + 1)
    }, 1000)
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    stopRecordingTimer()
    if (recordingState !== 'error') {
      setRecordingState('stopped')
    }
  }

  async function handleUploadVoiceProfile() {
    if (!enrollmentModal) {
      return
    }

    if (!audioBlob) {
      setRecordingError('Please record a sample before uploading.')
      return
    }

    if (!consentChecked) {
      setRecordingError('Consent is required before enrolling a voice profile.')
      return
    }

    if (recordingSeconds < 3) {
      setRecordingError('Please record at least a few seconds of speech.')
      return
    }

    try {
      setRecordingState('uploading')
      setRecordingError('')

      const wavBlob = await convertToWav(audioBlob)
      const result = enrollmentModal.mode === 'update'
        ? await updateVoiceProfile(enrollmentModal.contact.id, wavBlob, consentChecked)
        : await createVoiceProfile(enrollmentModal.contact.id, wavBlob, consentChecked)

      if (result?.status === 'ACTIVE' || result?.status === 'FAILED' || result?.status === 'PROCESSING') {
        await refreshVoiceProfile(enrollmentModal.contact.id)
      }

      setRecordingState('success')
    } catch (err: unknown) {
      console.error(err)
      setRecordingError(getApiErrorMessage(err, 'Recording failed. Please try again.'))
      setRecordingState('error')
    }
  }

  async function removeVoiceProfile(contact: Contact) {
    const confirmed = window.confirm(`Remove trusted voice verification for ${contact.nickname}?`)
    if (!confirmed) {
      return
    }

    try {
      setVoiceProfileLoading((current) => ({
        ...current,
        [contact.id]: true,
      }))
      await deleteVoiceProfile(contact.id)
      await refreshVoiceProfile(contact.id)
    } catch (err: unknown) {
      console.error(err)
      setError(getApiErrorMessage(err, 'Unable to remove the voice profile.'))
    } finally {
      setVoiceProfileLoading((current) => ({
        ...current,
        [contact.id]: false,
      }))
    }
  }

  const trustedCount = contacts.filter((contact) => contact.is_trusted).length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-cyan-400">
            Identity Protection
          </p>
          <h1 className="mt-1 text-3xl font-bold text-white">
            Trusted Contacts
          </h1>
          <p className="mt-2 text-slate-400">
            Manage trusted contacts used for speaker verification.
          </p>
        </div>

        <button
          onClick={() => {
            if (showAddForm) {
              resetAddForm()
            } else {
              setShowAddForm(true)
              setError('')
            }
          }}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-500 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
        >
          {showAddForm ? <X size={18} /> : <Plus size={18} />}
          {showAddForm ? 'Cancel' : 'Add Contact'}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-cyan-500/10 p-3">
              <UserRound size={20} className="text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{contacts.length}</p>
              <p className="text-sm text-slate-400">Total Contacts</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-500/10 p-3">
              <Shield size={20} className="text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{trustedCount}</p>
              <p className="text-sm text-slate-400">Trusted</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/10 p-3">
              <Check size={20} className="text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{contacts.length - trustedCount}</p>
              <p className="text-sm text-slate-400">Untrusted</p>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {showAddForm && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold text-white">Add Trusted Contact</h2>
          <p className="mt-1 text-sm text-slate-400">
            Search for another registered Saksham 2.0 user.
          </p>

          <form onSubmit={handleAddContact} className="mt-5 space-y-5">
            <div>
              <label htmlFor="userSearch" className="mb-2 block text-sm font-medium text-slate-300">
                Search Saksham 2.0 User
              </label>
              <input
                id="userSearch"
                value={searchQuery}
                onChange={(event) => handleUserSearch(event.target.value)}
                placeholder="Search by username..."
                autoComplete="off"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
              />

              {searching && (
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                  <Loader2 size={14} className="animate-spin" />
                  Searching users...
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="mt-2 overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
                  {searchResults.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => selectUser(user)}
                      className="flex w-full items-center gap-3 border-b border-slate-800 px-4 py-3 text-left transition last:border-b-0 hover:bg-slate-800"
                    >
                      <div className="rounded-full bg-slate-800 p-2">
                        <UserRound size={18} className="text-cyan-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">{user.display_name}</p>
                        <p className="text-xs text-slate-500">@{user.username}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {selectedUser && (
                <div className="mt-3 flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-emerald-500/10 p-2">
                      <UserRound size={18} className="text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{selectedUser.display_name}</p>
                      <p className="text-xs text-slate-400">@{selectedUser.username}</p>
                    </div>
                  </div>
                  <Check size={20} className="text-emerald-400" />
                </div>
              )}
            </div>

            <div>
              <label htmlFor="nickname" className="mb-2 block text-sm font-medium text-slate-300">
                Nickname
              </label>
              <input
                id="nickname"
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
                required
                placeholder="Brother, Mother, Manager..."
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-500"
              />
            </div>

            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={isTrusted}
                onChange={(event) => setIsTrusted(event.target.checked)}
                className="h-4 w-4"
              />
              <span className="text-sm text-slate-300">Mark as trusted contact</span>
            </label>

            <div>
              <button
                type="submit"
                disabled={submitting || !selectedUser}
                className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting && <Loader2 size={17} className="animate-spin" />}
                Add Contact
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-xl border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 px-6 py-5">
          <h2 className="text-lg font-semibold text-white">Your Contacts</h2>
          <p className="mt-1 text-sm text-slate-400">
            Contacts available for identity verification.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center px-6 py-16">
            <Loader2 className="animate-spin text-cyan-400" size={28} />
          </div>
        ) : contacts.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <div className="mx-auto mb-4 w-fit rounded-full bg-slate-800 p-4">
              <UserRound size={28} className="text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white">No contacts yet</h3>
            <p className="mt-2 text-sm text-slate-400">
              Add a trusted contact to prepare for speaker verification.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {contacts.map((contact) => {
              const profile = voiceProfiles[contact.id] ?? EMPTY_PROFILE

              return (
                <div key={contact.id} className="px-6 py-5">
                  {editingId === contact.id ? (
                    <div className="flex flex-col gap-4 md:flex-row md:items-center">
                      <input
                        value={editNickname}
                        onChange={(event) => setEditNickname(event.target.value)}
                        className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 text-white outline-none focus:border-cyan-500"
                      />

                      <label className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          checked={editTrusted}
                          onChange={(event) => setEditTrusted(event.target.checked)}
                        />
                        Trusted
                      </label>

                      <button
                        onClick={() => handleUpdate(contact.id)}
                        disabled={submitting}
                        className="rounded-lg bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
                      >
                        Save
                      </button>

                      <button
                        onClick={cancelEditing}
                        className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div className="flex items-center gap-4">
                        <div className="rounded-full bg-slate-800 p-3">
                          <UserRound size={22} className="text-cyan-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-3">
                            <h3 className="font-semibold text-white">{contact.nickname}</h3>
                            {contact.is_trusted && (
                              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                                Trusted
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-slate-500">User ID: {contact.contact_user_id}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => startEditing(contact)}
                          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
                        >
                          <Edit3 size={15} />
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCall(contact.contact_user_id)}
                          className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/30 px-4 py-2 text-sm text-cyan-400 transition hover:bg-cyan-500/10"
                        >
                          <Phone className="h-4 w-4" />
                          Call
                        </button>
                        <button
                          onClick={() => handleDelete(contact.id)}
                          className="inline-flex items-center gap-2 rounded-lg border border-red-500/20 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10"
                        >
                          <Trash2 size={15} />
                          Delete
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                          Voice Profile
                        </p>
                        <div className="mt-1 flex items-center gap-2">
                          <span
                            className={`rounded-full border px-2.5 py-1 text-xs font-medium ${getVoiceProfileBadgeClasses(profile.status)}`}
                          >
                            {formatVoiceProfileStatus(profile.status)}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {profile.status === 'ACTIVE' && (
                          <>
                            <button
                              type="button"
                              onClick={() => openEnrollmentModal(contact, 'update')}
                              disabled={voiceProfileLoading[contact.id]}
                              className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 px-3 py-2 text-sm font-medium text-cyan-300 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              Re-enroll
                            </button>
                            <button
                              type="button"
                              onClick={() => removeVoiceProfile(contact)}
                              disabled={voiceProfileLoading[contact.id]}
                              className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm font-medium text-red-300 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              Remove Voice Profile
                            </button>
                          </>
                        )}

                        {(profile.status === 'NOT_ENROLLED' || profile.status === 'REVOKED' || profile.status === 'FAILED') && (
                          <button
                            type="button"
                            onClick={() => openEnrollmentModal(contact, 'create')}
                            disabled={voiceProfileLoading[contact.id]}
                            className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {profile.status === 'FAILED' ? 'Retry Enrollment' : 'Enroll Voice'}
                          </button>
                        )}

                        {profile.status === 'PROCESSING' && (
                          <button
                            type="button"
                            disabled
                            className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-sm font-medium text-amber-300"
                          >
                            Processing
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <Modal
        isOpen={Boolean(enrollmentModal)}
        onClose={closeEnrollmentModal}
        title={
          enrollmentModal
            ? `${enrollmentModal.mode === 'update' ? 'Re-enroll' : 'Enroll'} voice profile for ${enrollmentModal.contact.nickname}`
            : 'Voice profile'
        }
      >
        {enrollmentModal && (
          <div className="space-y-5">
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                Trusted Contact
              </p>
              <div className="mt-2 flex items-center gap-3">
                <div className="rounded-full bg-cyan-500/10 p-2">
                  <UserRound size={18} className="text-cyan-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">{enrollmentModal.contact.nickname}</p>
                  <p className="text-xs text-slate-400">{enrollmentModal.contact.contact_user_id}</p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-slate-300">Microphone status</p>
                <span
                  className={`rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-[0.15em] ${getRecordingStatusClasses(recordingState, permissionError)}`}
                >
                  {permissionError
                    ? 'Permission required'
                    : recordingState === 'recording'
                      ? 'Recording'
                      : recordingState === 'ready' || recordingState === 'stopped'
                        ? 'Ready'
                        : recordingState === 'uploading'
                          ? 'Uploading'
                          : recordingState === 'success'
                            ? 'Success'
                            : 'Waiting'}
                </span>
              </div>

              {permissionError && <p className="mt-3 text-sm text-red-400">{permissionError}</p>}
              {recordingError && <p className="mt-3 text-sm text-red-400">{recordingError}</p>}

              {recordingState !== 'success' && (
                <>
                  <label className="mt-4 flex items-start gap-3 rounded-lg border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      checked={consentChecked}
                      onChange={(event) => setConsentChecked(event.target.checked)}
                      className="mt-1 h-4 w-4"
                    />
                    <span>
                      I consent to using this voice recording to create a trusted speaker verification profile.
                    </span>
                  </label>

                  <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-300">Recording</p>
                      <span className="text-sm font-medium text-cyan-300">{formatRecordingTime(recordingSeconds)}</span>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={recordingState === 'recording' ? stopRecording : startRecording}
                        disabled={recordingState === 'uploading' || recordingState === 'requesting'}
                        className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold ${
                          recordingState === 'recording'
                            ? 'bg-red-500 text-white hover:bg-red-400'
                            : 'bg-cyan-500 text-slate-950 hover:bg-cyan-400'
                        } disabled:cursor-not-allowed disabled:opacity-50`}
                      >
                        {recordingState === 'recording' ? <MicOff size={16} /> : <Mic size={16} />}
                        {recordingState === 'recording' ? 'Stop' : 'Record'}
                      </button>

                      {audioBlob && (
                        <button
                          type="button"
                          onClick={resetRecordingSession}
                          className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:bg-slate-800"
                        >
                          Retry
                        </button>
                      )}
                    </div>

                    {audioUrl && (
                      <div className="mt-4">
                        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-400">Preview</p>
                        <audio controls src={audioUrl} className="w-full" />
                      </div>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleUploadVoiceProfile}
                    disabled={!audioBlob || !consentChecked || recordingState === 'uploading' || recordingSeconds < 3}
                    className="w-full rounded-lg bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {recordingState === 'uploading' ? 'Uploading...' : 'Upload Voice Profile'}
                  </button>
                </>
              )}

              {recordingState === 'success' && (
                <div className="mt-4 rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-300">
                  Voice profile enrolled successfully. The trusted contact status was refreshed immediately.
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

function formatVoiceProfileStatus(status: VoiceProfileStatus): string {
  switch (status) {
    case 'ACTIVE':
      return 'ACTIVE'
    case 'NOT_ENROLLED':
      return 'NOT ENROLLED'
    case 'PROCESSING':
      return 'PROCESSING'
    case 'FAILED':
      return 'FAILED'
    case 'REVOKED':
      return 'REVOKED'
    default:
      return 'NOT ENROLLED'
  }
}

function getVoiceProfileBadgeClasses(status: VoiceProfileStatus): string {
  switch (status) {
    case 'ACTIVE':
      return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
    case 'NOT_ENROLLED':
    case 'REVOKED':
      return 'border-slate-600 bg-slate-800 text-slate-300'
    case 'PROCESSING':
      return 'border-amber-500/20 bg-amber-500/10 text-amber-300'
    case 'FAILED':
      return 'border-red-500/20 bg-red-500/10 text-red-300'
    default:
      return 'border-slate-600 bg-slate-800 text-slate-300'
  }
}

function getRecordingStatusClasses(state: string, permissionError: string): string {
  if (permissionError) return 'border-red-500/20 bg-red-500/10 text-red-300'
  if (state === 'recording') return 'border-cyan-500/20 bg-cyan-500/10 text-cyan-300'
  if (state === 'success') return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
  if (state === 'uploading') return 'border-amber-500/20 bg-amber-500/10 text-amber-300'
  return 'border-slate-700 bg-slate-800 text-slate-300'
}

function formatRecordingTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

async function convertToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer()
  const audioContext = new AudioContext()

  try {
    const decoded = await audioContext.decodeAudioData(arrayBuffer.slice(0))
    const channelData = decoded.numberOfChannels > 1 ? new Float32Array(decoded.length) : decoded.getChannelData(0)

    if (decoded.numberOfChannels > 1) {
      const left = decoded.getChannelData(0)
      const right = decoded.getChannelData(1)
      for (let index = 0; index < decoded.length; index += 1) {
        channelData[index] = (left[index] + right[index]) / 2
      }
    }

    const wavBuffer = new ArrayBuffer(44 + channelData.length * 2)
    const view = new DataView(wavBuffer)
    writeString(view, 0, 'RIFF')
    view.setUint32(4, 36 + channelData.length * 2, true)
    writeString(view, 8, 'WAVE')
    writeString(view, 12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true)
    view.setUint16(22, 1, true)
    view.setUint32(24, decoded.sampleRate, true)
    view.setUint32(28, decoded.sampleRate * 2, true)
    view.setUint16(32, 2, true)
    view.setUint16(34, 16, true)
    writeString(view, 36, 'data')
    view.setUint32(40, channelData.length * 2, true)

    let offset = 44
    for (let index = 0; index < channelData.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[index]))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
      offset += 2
    }

    return new Blob([wavBuffer], { type: 'audio/wav' })
  } finally {
    await audioContext.close()
  }
}

function writeString(view: DataView, offset: number, value: string): void {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index))
  }
}
