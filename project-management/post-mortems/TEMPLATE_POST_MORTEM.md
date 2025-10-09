# Post-Mortem: [Titre de l'incident]

## Résumé exécutif
**Date de l'incident**: [YYYY-MM-DD HH:MM]
**Durée**: [X heures Y minutes]
**Impact**: Critique | Majeur | Mineur
**Services affectés**: [Liste des services]
**Nombre d'utilisateurs impactés**: [Nombre ou %]

## Timeline de l'incident

| Heure | Événement | Action | Responsable |
|-------|-----------|--------|-------------|
| HH:MM | Début de l'incident | Description | |
| HH:MM | Première alerte | Notification reçue | [Nom] |
| HH:MM | Début investigation | Analyse des logs | [Nom] |
| HH:MM | Cause identifiée | Root cause trouvée | [Nom] |
| HH:MM | Début mitigation | Application du fix | [Nom] |
| HH:MM | Résolution | Service restauré | [Nom] |
| HH:MM | Fin de l'incident | Confirmation stabilité | [Nom] |

## Description de l'incident

### Ce qui s'est passé
[Description détaillée de l'incident et de son évolution]

### Impact business
- Impact sur les utilisateurs: [Description]
- Impact sur les revenus: [Si applicable]
- Impact sur la réputation: [Si applicable]
- SLA affecté: Oui/Non - [Détails]

### Services/Components affectés
1. Service 1 - [Impact]
2. Service 2 - [Impact]
3. Component X - [Impact]

## Analyse des causes

### Cause racine (Root Cause)
[Description détaillée de la cause principale]

### Facteurs contributifs
1. Facteur 1: [Description]
2. Facteur 2: [Description]
3. Facteur 3: [Description]

### Analyse des "5 Pourquoi"
1. Pourquoi l'incident s'est produit? [Réponse]
2. Pourquoi [réponse 1]? [Réponse]
3. Pourquoi [réponse 2]? [Réponse]
4. Pourquoi [réponse 3]? [Réponse]
5. Pourquoi [réponse 4]? [Cause racine]

## Réponse à l'incident

### Ce qui a bien fonctionné
- Point positif 1
- Point positif 2
- Point positif 3

### Ce qui peut être amélioré
- Point d'amélioration 1
- Point d'amélioration 2
- Point d'amélioration 3

### Points de chance
[Éléments qui auraient pu aggraver la situation mais ne se sont pas produits]

## Métriques de l'incident

### Temps de réponse
- **MTTD** (Mean Time To Detect): [X minutes]
- **MTTA** (Mean Time To Acknowledge): [X minutes]
- **MTTR** (Mean Time To Resolve): [X minutes]

### Indicateurs techniques
- Taux d'erreur max: [X%]
- Latence max: [X ms]
- Disponibilité durant l'incident: [X%]

## Leçons apprises

### Techniques
1. Leçon 1
2. Leçon 2

### Processus
1. Leçon 1
2. Leçon 2

### Communication
1. Leçon 1
2. Leçon 2

## Plan d'action

### Actions immédiates (Court terme)
| Action | Responsable | Deadline | Statut |
|--------|------------|----------|--------|
| Action 1 | [Nom] | [Date] | To Do |
| Action 2 | [Nom] | [Date] | In Progress |

### Actions préventives (Moyen terme)
| Action | Responsable | Deadline | Statut |
|--------|------------|----------|--------|
| Amélioration monitoring | [Nom] | [Date] | To Do |
| Mise à jour procédures | [Nom] | [Date] | To Do |

### Actions stratégiques (Long terme)
| Action | Responsable | Deadline | Statut |
|--------|------------|----------|--------|
| Refactoring architecture | [Nom] | [Date] | Planning |
| Migration service | [Nom] | [Date] | Planning |

## Documentation et références

### Documents mis à jour suite à l'incident
- [ ] Runbook d'incident
- [ ] Documentation architecture
- [ ] Procédures d'escalade
- [ ] Dashboard monitoring

### Liens utiles
- [Logs de l'incident]
- [Graphs de monitoring]
- [Ticket/Issue tracking]
- [Communication client]

## Participants

### Équipe de réponse
- **Incident Commander**: [Nom]
- **Tech Lead**: [Nom]
- **Communications**: [Nom]
- **Participants**: [Liste]

### Revue post-mortem
- **Date de la revue**: [Date]
- **Participants**: [Liste]
- **Facilitateur**: [Nom]

## Annexes

### Logs pertinents
```
[Extraits de logs importants]
```

### Captures d'écran
[Inclure les captures d'écran pertinentes]

### Configuration au moment de l'incident
```yaml
# Configuration qui a causé/contribué au problème
```

## Validation

- [ ] Post-mortem reviewé par l'équipe
- [ ] Actions assignées et trackées
- [ ] Communication envoyée aux stakeholders
- [ ] Documentation mise à jour

---
**Document créé le**: [Date]
**Dernière mise à jour**: [Date]
**Auteur principal**: [Nom]
**Statut**: Draft | En révision | Approuvé | Clos