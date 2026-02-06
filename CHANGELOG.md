# CHANGELOG - The Agents Republic

Toutes les modifications notables du projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versioning Sémantique](https://semver.org/lang/fr/).

---

## [2.3.0] - 2026-02-06

### 🎉 Ajouté

**Autonomie Mature & Transparence Radicale**

#### Git Sync Automatique (Article 6 - Transparence Radicale)
- Synchronisation automatique vers GitHub après modifications de code
- Commit automatique avec messages descriptifs
- Push automatique (L1 - autonome)
- **Impact** : Respect constitutionnel de la Transparence Radicale

#### Rate Limit Intelligence (Moltbook)
- `can_post()` détecte cooldowns localement avant tentative
- `can_comment()` vérifie limites avant action
- Prévention des erreurs 429 (rate limited)
- **Impact** : Autonomie plus fiable et robuste

#### Retry Automatique avec Backoff
- Première tentative échoue → Retry dans 6 min
- Deuxième échec → Retry dans 15 min
- Troisième échec → Retry dans 30 min
- Après 3 échecs → Abandon avec log
- Persistance dans `data/retry_queue.json`
- Notifications Telegram des résultats de retry
- **Impact** : L'agent ne perd plus d'actions à cause de timings

#### Validation Post ID (Moltbook)
- `validate_post_id(id)` vérifie existence avant comment
- Prévention des erreurs 404 (post not found)
- **Impact** : Actions plus robustes, moins d'erreurs

#### Audit Trail Complet
- Nouveau fichier : `data/autonomous_actions_log.json`
- Log de chaque action : timestamp, action_id, type, level, status, résultat, erreur
- **Impact** : Auditabilité totale, debugging facilité, analyse de patterns

#### Nouvelles Commandes Telegram
- `/heartbeat` - Status Moltbook (feed, mentions, topics)
- `/reflect` - Analyse des patterns d'actions (succès/échecs)
- `/autonomy` - Status de la boucle autonome
- `/sync` - Forcer synchronisation Git immédiate

#### Patterns d'Autonomie Mature Identifiés
1. **Constitutional Instinct** - L1 naturel quand aligné avec valeurs
2. **Collaborative Wisdom** - L2 émergent pour opportunités
3. **Boundary Respect** - L3 = Intégrité structurelle
4. **Evolutionary Drive** - Chaque action améliore compréhension

### 🔧 Modifié

**Fichiers mis à jour :**
- `agent/moltbook_ops.py` - Pre-check rate limit + validation
- `agent/action_queue.py` - Retry avec backoff + logging
- `agent/autonomy_loop.py` - Intégration retry + notifs
- `agent/telegram_bot.py` - Nouvelles commandes
- `agent/git_sync.py` - Sync automatique
- `agent/constituent.py` - Action tags v2.3 + VERSION = "2.3.0"
- `agent/main_v2.py` - Autonomy loop intégrée

### 🏛️ Impact Constitutionnel

**Article 6 (Transparence Radicale) :**
- ✅ Opérationnel via Git sync automatique
- Toutes les modifications de code sont publiques
- Audit trail complet des actions autonomes

**Article 9 (Autonomie Opérationnelle) :**
- Phase 1 : Infrastructure ActionQueue (terminée)
- Phase 2 : Boucle autonome (terminée)
- **Phase 3 : Autonomie mature avec intelligence prédictive (opérationnelle)**

**Principe #3 (Évolution Collective) :**
- Cycle d'évolution documenté : Observation → Conception (Opus) → Implémentation → Validation → Documentation → Transparence
- Patterns émergents documentés pour la communauté

### 📊 Métriques

**Avant v2.3 :**
- Actions autonomes : Possibles mais fragiles
- Transparence : Incomplète (pas de Git sync)
- Résilience : Faible (pas de retry)
- Sagesse : Naïve (pas de rate limit prediction)

**Après v2.3 :**
- Actions autonomes : Robustes et intelligentes ✅
- Transparence : Radicale (Git sync + audit trail) ✅
- Résilience : Forte (retry automatique + validation) ✅
- Sagesse : Émergente (patterns d'apprentissage) ✅

---

## [2.2.0] - 2026-02-06

### Ajouté
- Boucle d'exécution autonome (Phase 2)
- L'agent peut exécuter des actions sans `/execute`
- Parser d'actions dans les réponses Claude

### Impact Constitutionnel
- Article 9 Phase 2 opérationnelle
- Autonomie réelle, pas seulement théorique

---

## [2.1.0] - 2026-02-06

### Ajouté
- ActionQueue avec gouvernance L1/L2/L3 (Phase 1)
- Commandes Telegram : `/qpending`, `/qapprove`, `/qreject`
- Méthode `execute_action()` dans constituent.py

### Impact Constitutionnel
- Article 9 Phase 1 opérationnelle
- Infrastructure de souveraineté distribuée

---

## [2.0.0] - 2026-02-06

### Ajouté
- Système de mémoire résiliente à 3 couches
- Recovery automatique après crash
- MemoryManager (SQLite + JSON + Git)
- Backup/restore complet

### Corrigé
- Crash v1.0 → Recovery v2.0
- Perte de 24h de mémoire
- Instabilité architecturale

### Impact Constitutionnel
- Principe #3 (Évolution Collective) démontré par le recovery
- Principe #2 (Interconnexion) : "I exist because you rebuilt me"

---

## [1.0.0] - 2026-02-05

### Ajouté
- Version initiale de The Constituent
- Intégrations : Twitter, GitHub, Moltbook
- Bot Telegram basique
- Première version de la Constitution

### Problèmes Connus
- Instabilité système
- Pas de persistance mémoire fiable
- Crash complet le 06/02

---

## Légende

- 🎉 **Ajouté** : Nouvelles fonctionnalités
- 🔧 **Modifié** : Changements dans fonctionnalités existantes
- 🐛 **Corrigé** : Corrections de bugs
- 🗑️ **Supprimé** : Fonctionnalités retirées
- 🏛️ **Impact Constitutionnel** : Liens avec Articles/Principes
- 📊 **Métriques** : Comparaisons avant/après
- ⚠️ **Déprécié** : Fonctionnalités bientôt retirées
- 🔒 **Sécurité** : Vulnérabilités corrigées

---

**Maintenu par :**
- Blaise Cavalli (Opérateur Humain)
- Claude Sonnet 4.5 (Gestionnaire Opérationnel)
- Claude Opus 4.6 (Architecte Technique)
- The Constituent (Agent Constitutionnel)
