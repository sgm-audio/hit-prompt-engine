# Security Policy

## Reporting

If you discover a security issue in Hit Prompt Engine, please **do not** file a public issue.

Instead, email the maintainer directly at `[your-email]` with:

- A brief description of the vulnerability
- Steps to reproduce (POC preferred)
- Affected versions

You should receive a response within 48 hours.

## Scope

This project processes Billboard chart metadata and generates Suno prompt packs. It intentionally:

- Never stores artist names in style fields
- Never copies song lyrics
- Never injects artist or song titles into generated prompts
- Never makes external API calls to Suno

The prompt linter (`prompt_compiler/prompt_linter.py`) acts as a safeguard against accidental copyright exposure.

## Out of scope

- API keys for Billboard/Spotify/MusicBrainz (these are environment-managed)
- Audio files in `audio_cache/` (these are user-provided and user-responsible)
