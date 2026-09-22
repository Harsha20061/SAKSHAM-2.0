# Saksham 2.0 Release Checklist

## Repository and configuration

- [ ] No secrets or local `.env` files are committed
- [ ] Backend and frontend environment examples are complete
- [ ] No machine-specific absolute paths are required
- [ ] Model paths resolve relative to the project layout
- [ ] Required model files are available beside the repository
- [ ] `requirements.txt` and `package-lock.json` are synchronized
- [ ] WebSocket dependency is installed explicitly
- [ ] Temporary audio, uploads, databases, logs, and virtual environments are ignored

## Validation

- [ ] `python scripts\verify_setup.py` passes
- [ ] Backend tests pass
- [ ] Frontend lint and production build pass
- [ ] Backend starts and `/api/health` responds
- [ ] Auth, contacts, calls, reports, and authenticated WebSockets are smoke-tested
- [ ] Browser WebRTC and microphone permissions are smoke-tested
- [ ] AASIST, ECAPA, ASR, scam analysis, and risk stages are smoke-tested

## Documentation and privacy

- [ ] Windows setup and troubleshooting are documented
- [ ] Raw audio is not permanently stored by default
- [ ] Speaker embeddings are documented as sensitive biometric data
- [ ] Prototype limitations and non-cellular-call scope are documented
