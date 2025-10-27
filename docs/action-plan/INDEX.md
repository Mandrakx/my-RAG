# Action Plan Index - Cross-Cutting Integration Fix

## 📍 Quick Navigation

**Main Action Plan**: [2025-10-26-fix-alignment-cross.md](./2025-10-26-fix-alignment-cross.md)

This folder contains the detailed action plan for fixing alignment between the iOS (mneia-lab), Transcript, and my-RAG services per ADR-2025-10-03-003 (Cross-Cutting Contract).

---

## 🎯 Executive Summary

| Component | Status | Blocker | Timeline |
|-----------|--------|---------|----------|
| **mneia-lab (iOS)** | 🔴 INCOMPLETE | ✅ YES | Nov 9, 2025 |
| **Transcript** | 🟢 STABLE | ❌ NO | Nov 2, 2025 (optional enhancements) |
| **my-RAG** | 🟢 STABLE | ❌ NO | Nov 23, 2025 (robustness) |

**Overall E2E Status**: 🟠 40% Ready (Blocked by iOS)

---

## 📋 What's in the Action Plan

The main file (`2025-10-26-fix-alignment-cross.md`) is organized as follows:

### 🍎 Project 1: MNEIA-LAB (iOS Transmission Client)
**Priority**: P0 CRITICAL BLOCKER | **Duration**: 2 weeks (Oct 26 - Nov 9)

**Themes** (with checkboxes):
- **A** — Identifier & Metadata Generation (external_event_id, trace_id, timezone)
- **B** — Device Information Capture (model, OS version, app version)
- **C** — GPS Enhancement (add accuracy_m)
- **D** — Participants Management (structured hints)
- **E** — Metadata Envelope Construction
- **F** — API Key Management (Keychain integration)
- **G** — Transcript API Client (auth + upload + polling)
- **H** — Retry & Error Handling (exponential backoff)
- **I** — Job Tracking & Local Persistence
- **J** — Integration Testing (unit + E2E)
- **K** — Documentation & Guides
- **L** — Code Review & Quality

### 🏗️ Project 2: TRANSCRIPT SERVICE
**Priority**: P1 ENHANCEMENTS | **Duration**: 2 weeks (Nov 2 - Nov 16, optional)

**Themes**:
- **A** — Documentation & Setup Guides
- **B** — Security Enhancements (scope-based auth, audit logging)
- **C** — Production Hardening (rate limiting)

### 📦 Project 3: MY-RAG INGESTION PIPELINE
**Priority**: P2 ROBUSTNESS | **Duration**: 2 weeks (Nov 9 - Nov 23)

**Themes**:
- **A** — Critical Alignment Fixes (external_event_id, trace_id)
- **B** — Distributed Locking for Duplicate Detection
- **C** — Retry Backoff Strategy (exponential backoff)
- **D** — NLP Mode Detection Improvements
- **E** — Producer Metadata Tracking
- **F** — SLA Monitoring & Alerts
- **G** — Archive Structure Validation
- **H** — Checksum Validation Enhancements
- **I** — Observability Enhancements
- **J** — Documentation
- **K** — Quality & Testing

### 🔄 Cross-Project Coordination
- **Theme A** — Integration Testing (staging → E2E → production)
- **Theme B** — Documentation Synchronization
- **Theme C** — Monitoring & Alerts Setup

---

## 🚀 How to Use This Plan

### For Project Leads:
1. Open [2025-10-26-fix-alignment-cross.md](./2025-10-26-fix-alignment-cross.md)
2. Find your project section (mneia-lab, Transcript, or my-RAG)
3. Identify your themes
4. Assign tasks to team members
5. Track progress using checkboxes

### For Team Members:
1. Check your assigned section
2. Each checkbox represents an atomic task (1-4 hours of work)
3. Update the checkbox as you progress (✓ = complete)
4. If blocked, comment on the pull request or escalate

### For Integration Leads:
1. Monitor weekly progress (every Friday)
2. Look for unchecked items in "Critical" sections
3. Coordinate between projects as needed
4. Run E2E tests after each phase

---

## 📊 Progress Tracking

To track progress, you can:

1. **Clone/fork the action plan** to your own branch:
   ```bash
   git checkout -b feature/action-plan-progress
   ```

2. **Update checkboxes** as work completes:
   ```markdown
   - [x] Task complete
   - [ ] Task pending
   ```

3. **Create a PR** with weekly updates
4. **Track in project management tool** (Jira, GitHub Projects, etc.)

---

## 🎯 Key Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| Oct 26 | Action plan published | ✅ DONE |
| Nov 1 | iOS Phase 1 (Metadata) complete | ⏳ PENDING |
| Nov 8 | iOS Phase 2 (API client) complete | ⏳ PENDING |
| Nov 9 | iOS Phase 3 (Testing) complete | ⏳ PENDING |
| Nov 9 | First E2E test (iOS → Transcript) | ⏳ PENDING |
| Nov 16 | Transcript enhancements (optional) | ⏳ PENDING |
| Nov 23 | my-RAG robustness improvements | ⏳ PENDING |
| Nov 30 | Production readiness validation | ⏳ PENDING |

---

## 🔗 Related Documents

- **ADR-2025-10-03-003**: [Cross-Cutting Audio → Transcript → RAG Contract](../../adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md)
- **ADR-2025-10-16-004**: [Alignment Implementation Plan](../../adr/ADR-2025-10-16-004-alignment-cross-cutting-contract.md)
- **ADR-2025-10-16-006**: [Authentication Architecture](../../adr/ADR-2025-10-16-006-authentication-authorization-architecture.md)

---

## 📞 Support

For questions about this action plan:
- **mneia-lab (iOS)**: Contact iOS Team (@ios-team on Slack)
- **Transcript**: Contact Backend Team (@transcript-team on Slack)
- **my-RAG**: Contact RAG Team (@rag-team on Slack)
- **Integration**: Contact Staff Architect (@staff-arch on Slack)

**Weekly Sync**: Monday 10:00 UTC (Teams/Slack)
**Escalation**: Flag critical blockers in #engineering-urgent

---

## 📝 Notes

- This plan assumes all three services start in October 2025
- iOS is on the critical path (blocks Transcript and my-RAG)
- Transcript and my-RAG can proceed in parallel with iOS work
- Each theme can be tackled independently (low coupling)
- Staging environment required for integration testing (Week 2+)

---

**Last Updated**: 2025-10-26
**Status**: 🟠 IN PROGRESS
**Next Review**: 2025-11-02
