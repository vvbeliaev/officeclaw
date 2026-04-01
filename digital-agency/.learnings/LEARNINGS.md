## [LRN-20260401-001] Pinterest antibots block automated moodboard research

**Logged**: 2026-04-01T15:45Z
**Priority**: high
**Status**: pending
**Area**: design

### Summary
Pinterest blocks automated access (antibots). Cannot scrape or fetch pins programmatically for moodboard collection.

### Details
When attempting to gather visual references for moodboard via Pinterest, the platform's antibots protection prevents automated access. This breaks the moodboard workflow which relies on Pinterest as primary reference source.

### Suggested Action
1. Update `moodboard.md` to document fallback sources: Dribbble, Behance, Awwwards
2. Add Pinterest credentials check at start of moodboard phase
3. If no credentials available → use fallback sources (Dribbble/Behance) and create local moodboard_research.md instead of Pinterest board
4. Consider asking client for Pinterest account access as part of onboarding

### Metadata
- Source: client_feedback (user noted Pinterest blocks)
- Related Files: skills/workflow/moodboard.md
- Tags: pinterest, antibots, moodboard, workflow-blocker
- See Also: none

---
