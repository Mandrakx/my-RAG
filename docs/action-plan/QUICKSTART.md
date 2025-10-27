# Quick Start Guide - Action Plan

**TL;DR**: Read this if you have 5 minutes, then move to the detailed documents.

---

## 🎯 What's This About?

Three services need to work together:
- **iOS (mneia-lab)**: Records audio + sends to backend
- **Transcript**: Processes audio + publishes results
- **my-RAG**: Ingests results + stores them

**Problem**: iOS is incomplete. Transcript & my-RAG are ready.

**Solution**: This action plan tells exactly what to build.

---

## ⏱️ Timeline

```
Week 1-2: iOS implements upload client (CRITICAL PATH)
Week 2-3: Full E2E testing
Week 4: Production ready
```

**Status**: 🔴 iOS BLOCKED (needs implementation)

---

## 📂 Files in This Folder

| File | Read Time | Purpose |
|------|-----------|---------|
| **2025-10-26-fix-alignment-cross.md** | 30 min | Main action plan (215+ tasks with checkboxes) |
| **INDEX.md** | 5 min | Navigation guide |
| **CODE_LOCATIONS.md** | 10 min | Where to create/modify each file |
| **PROGRESS_TEMPLATE.md** | 5 min | Weekly status report template |
| **DELIVERABLES_SUMMARY.md** | 10 min | What was created + metrics |
| **QUICKSTART.md** | 5 min | This file! |

---

## 🚀 For Project Leads (What to Do Now)

### iOS Lead:
1. Open: `2025-10-26-fix-alignment-cross.md`
2. Find: "PROJECT 1: MNEIA-LAB"
3. Themes to tackle Week 1:
   - **Theme A**: Generate external_event_id + trace_id
   - **Theme B**: Capture device info (model, OS, app version)
   - **Theme C**: Extend GPS with accuracy_m
4. Assign tasks to team members
5. Start Monday Oct 26

### Transcript Lead:
1. Most work already done ✅
2. Optional: Theme A (Documentation for iOS clients)
3. No blockers

### my-RAG Lead:
1. Currently stable ✅
2. Can start Theme A fixes anytime
3. Will need Transcript data for full testing

---

## 📋 For Team Members (What to Do)

1. **Get assignment** from your lead
2. **Find it** in the main action plan document
3. **Check file locations** in CODE_LOCATIONS.md
4. **Implement** the feature
5. **Write tests** (checkbox = test included)
6. **Update checkbox** when done
7. **Create PR** with your changes

---

## 🔑 Key Facts

| Fact | Details |
|------|---------|
| **Critical Blocker** | iOS API client not implemented |
| **Effort** | ~300 person-hours total |
| **High Risk Items** | iOS Theme F-G (API client + auth) |
| **Weekly Check-in** | Monday 10:00 UTC |
| **Success Metric** | E2E audio flow iOS → Transcript → my-RAG |

---

## 🚨 What's Blocking Us?

### iOS is missing:
- ❌ API client for Transcript upload
- ❌ external_event_id generation
- ❌ trace_id generation
- ❌ device info capture (model, OS, app version)
- ❌ API key management (Keychain)
- ❌ Checksum calculation

### Transcript is ready:
- ✅ Authentication
- ✅ Upload endpoints
- ✅ Archive generation
- ✅ Redis message publishing

### my-RAG is ready:
- ✅ Message consumer
- ✅ Validation logic
- ✅ Checksum verification
- ✅ DLQ error handling

---

## 📞 Quick Help

**iOS Questions**: @ios-team on Slack
**Transcript Questions**: @transcript-team on Slack
**my-RAG Questions**: @rag-team on Slack
**Integration Questions**: @staff-arch on Slack

**Urgent Blockers**: Post in #engineering-urgent

---

## 📖 Next Steps

1. **Read this whole folder** (start with INDEX.md)
2. **Open the main plan** (2025-10-26-fix-alignment-cross.md)
3. **Find your project** (iOS, Transcript, or my-RAG)
4. **Assign themes** to team members
5. **Start Week 1 work** (Monday Oct 26)
6. **Weekly sync** (Monday 10:00 UTC starting Oct 26)

---

## 💡 Pro Tips

✅ **DO**:
- Update checkboxes as you work
- Create weekly progress reports
- Escalate blockers immediately
- Run integration tests early
- Coordinate across teams

❌ **DON'T**:
- Wait until the end to test
- Skip documentation
- Skip unit tests
- Work in isolation
- Merge without PR review

---

## 🎓 Reading Order (Recommended)

1. **This file** (5 min) ← You are here
2. **INDEX.md** (5 min) — Navigation guide
3. **2025-10-26-fix-alignment-cross.md** (30 min) — Find your project + theme
4. **CODE_LOCATIONS.md** (5 min) — When you start coding
5. **PROGRESS_TEMPLATE.md** (5 min) — At end of week

---

## ✅ Success Looks Like

✅ External audio recording flows from iOS → Transcript → my-RAG
✅ trace_id visible in logs across all three systems
✅ All metadata fields present per ADR-2025-10-03-003
✅ Errors handled gracefully with DLQ routing
✅ Metrics show SLA compliance (p95 < 5s)
✅ Full E2E test passing in staging

---

## 📅 Key Dates

| Date | Milestone |
|------|-----------|
| Oct 26 | Kickoff |
| Nov 1 | iOS Phase 1 (metadata) |
| Nov 8 | iOS Phase 2 (API client) |
| Nov 9 | First E2E test |
| Nov 30 | Production ready |

---

## 🔗 Related Documents

- **ADR-2025-10-03-003**: The contract we're implementing
- **ADR-2025-10-16-004**: my-RAG alignment plan
- **ADR-2025-10-16-006**: Authentication architecture

---

**Ready to dive in?** → Open **2025-10-26-fix-alignment-cross.md** now!

Questions? Post in #engineering or @staff-arch on Slack.
