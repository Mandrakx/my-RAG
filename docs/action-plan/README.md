# Action Plan RAG

## Phase 0 - Preparation & cadrage (terminee)
- [x] Passer en revue `docs/specifications/SPEC_CONVERSATION_RAG.md` et consolider les besoins fonctionnels.
- [x] Verifier `docs/specifications/Spec-analyse-fichiers.md` pour les dependances futures.
- [x] Lister contraintes materiel (RTX 3090) et cibles cloud pour preparer la portabilite.

## Phase 1 - Design initial du POC (terminee)
- [x] Formaliser le plan d''implementation global base sur les specifications.
- [x] Rediger `docs/design/RAG-initial-design.md` avec architecture, pipeline, securite, roadmap.
- [x] Documenter le contrat d''integration audio avec depot MinIO et notifications Redis.

## Phase 2 - Alignement avec le projet audio (en cours)
- [x] Finaliser le workflow drop MinIO avec l''equipe audio (cf. docs/design/cross-cutting-concern.md et docs/guides/operations/minio-drop-playbook.md) :
  - [x] Definir la structure exacte du paquet depose sur MinIO : archive tar.gz obligatoire, arborescence des fichiers, nommage standard et encodage JSON du transcript.
  - [x] Confirmer les delais et retrys (ack <5s, fenetre de retention, procedure de relivraison).
  - [x] Designer les responsabilites: publication notification Redis, suivi deadletters, correction des erreurs.
  - [x] Rediger les playbooks d'exploitation (checklist depot, checklist ingestion) – voir docs/guides/operations/minio-drop-playbook.md.
- [x] Documenter les exigences partagees dans `docs/design/cross-cutting-concern.md`.
- [x] Definir le schema exact de message Redis Streams et les codes d''erreur partages (docs/design/cross-cutting-concern.md + docs/design/audio-redis-message-schema.json).
- [x] Documenter le plan de monitoring ingestion (logs correles, metriques Prometheus, alertes) - voir monitoring/ingestion-monitoring-plan.md.

## Phase 3 - Environnement local & infrastructure (a faire)
- [ ] Finaliser la topologie Docker Compose (services, reseaux, volumes, secrets).
- [ ] Script d''installation MinIO local (bucket `ingestion/drop`, politiques d''acces, rotation cles).
- [ ] Definir la strategie de gestion des secrets (.env exemples, integration future secret manager).

## Phase 4 - Pipeline ingestion & stockage (a faire)
- [ ] Developper le watcher MinIO et le consommateur Redis pour declencher l''orchestration.
- [ ] Implementer la normalisation transcript -> `conversation.jsonl` avec validations JSON Schema.
- [ ] Assurer la persistence: stockage brut dans MinIO, enregistrement des metadonnees et statuts dans PostgreSQL.

## Phase 5 - Stack NLP GPU (a faire)
- [ ] Benchmarks RTX 3090 pour selectionner embeddings, NER et LLM (VRAM, throughput, qualite).
- [ ] Implementer le pipeline chunking + embeddings + indexation Qdrant.
- [ ] Deployer les services d''extraction NER/relations familiales avec cache Redis.
- [ ] Integrer reranker GPU et moteur de generation (vLLM/TGI) avec strategies de partage VRAM.

## Phase 6 - API & experience utilisateur (a faire)
- [ ] Exposer l''API FastAPI v1 (upload external, search, profiles, intelligence, exports) + OpenAPI.
- [ ] Implementer la generation de suggestions et l''export PDF via le backend.
- [ ] Prototyper l''interface POC (Next.js/Tauri) pour recherche, fiches profil, timeline.

## Phase 7 - Qualite, securite, observabilite (a faire)
- [ ] Mettre en place tests unitaires et scenarios end-to-end du pipeline conversationnel.
- [ ] Configurer Prometheus/Grafana, alerting, et journalisation structuree (correlation ids, speakers).
- [ ] Implementer chiffrement des donnees, RBAC, gestion du consentement et audit trail.

## Phase 8 - Preparation migration cloud (a faire)
- [ ] Containeriser l''ensemble des services avec publication sur le registry cible.
- [ ] Rediger les manifests Helm et le socle Terraform (reseau, GPU nodes, services manages).
- [ ] Preparer les scripts de migration de donnees (pg_dump, snapshot Qdrant, sync MinIO -> S3/GCS).
- [ ] Definir la strategie CI/CD (GitHub Actions) pour builds, tests, deploiements.


