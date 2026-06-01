# Mise à jour des dépendances : click-extra, rich-click, rich

> **Pour les agents :** SUB-SKILL REQUIS : Utiliser superpowers:subagent-driven-development (recommandé) ou superpowers:executing-plans pour exécuter ce plan tâche par tâche. Les étapes utilisent la syntaxe checkbox (`- [ ]`) pour le suivi.

**Objectif :** Monter `click-extra` 7.16.1→7.18.0, `rich` 13.9.4→15.0.0, `rich-click` 1.9.7→1.9.8 sans régression.

**Architecture :** Simple montée de version — aucun changement de code source attendu. Les trois mises à jour sont couplées : click-extra 7.17.0+ tire Click 8.4.1 (contre 8.3.3 actuellement), et rich-click 1.9.8 a été publié précisément pour corriger la compatibilité avec Click 8.4.x. Les trois doivent arriver ensemble. La contrainte `rich>=13.0` autorise déjà la 15.x ; seules les bornes minimales changent.

**Stack :** uv, pytest, ruff, click-extra, rich, rich-click, click (transitif)

---

## Audit des breaking changes (pré-recherche, ne pas sauter)

### rich 13.9.4 → 15.0.0

| Version | Breaking change | Impact sur pyclif |
|---------|----------------|-----------------|
| 14.0.0 | `NO_COLOR=` (vide) ne désactive plus les couleurs ; avant, toute présence de la variable suffisait | Aucun test ni CI ne définit `NO_COLOR=` — confirmé par grep |
| 14.0.0 | `FORCE_COLOR=` (vide) — même règle | Idem — aucun impact |
| 15.0.0 | Python 3.8 abandonné | pyclif requiert ≥3.10 — aucun impact |

Aucune API supprimée ou renommée utilisée par pyclif (`Console`, `Panel`, `Table`, `RichHandler`, `Live`, `Status`, `Prompt`, `Rule`, `Syntax`, `Text`, `box` — tous inchangés).

Effets visuels (pas des breaking changes, mais observables) :
- Fond du titre des `Panel` corrigé (14.1.0) — les panneaux s'afficheront plus correctement
- L'imbrication de `Live` est maintenant autorisée (14.1.0)

### click-extra 7.16.1 → 7.18.0

| Symbole supprimé | Utilisé dans pyclif ? | Verdict |
|-----------------|----------------------|---------|
| Module `click_extra.themes` | Non | Sûr |
| Constantes `DARK`, `DRACULA`, `LIGHT`, `MONOKAI`, `NORD`, `SOLARIZED_DARK` | Non | Sûr |
| Attribut `default_theme` | Non — pyclif utilise déjà `get_default_theme()` dans `core/log/formatters.py:5` | Sûr |
| Constantes pré-rendues `OK`, `KO` | Non | Sûr |
| Attribut `ctx.telemetry` | Non | Sûr |
| Callback `disable_colors` sur `ColorOption` | Non | Sûr |
| **Chemins de sous-modules** `click_extra.jobs`, `click_extra.timer` supprimés | `TimerOption` est utilisé (`classes.py:11`, `decorators.py:113`) mais importé via `from click_extra import TimerOption` (racine) — pas via le chemin de sous-module supprimé. | Sûr |
| `ValueError` au chargement de `--config` → maintenant `SystemExit` | Aucun test n'exerce ce chemin d'erreur | Sûr |

Upgrade transitif : Click 8.3.3 → 8.4.1 (requis par click-extra 7.17.0+). Aucune suppression d'API Click 8.4.x n'affecte pyclif.

### rich-click 1.9.7 → 1.9.8

Uniquement un correctif : répare le mécanisme de patching de rich-click cassé par Click 8.4.0. **Doit être mis à jour en même temps que click-extra.**

---

## Fichiers à modifier

| Fichier | Changement |
|---------|-----------|
| `pyproject.toml` | Monter trois bornes minimales de dépendances |
| `uv.lock` | Régénéré automatiquement par `uv sync` |

Aucun changement de fichier source ou de test prévu. Si un test échoue après la mise à jour, une tâche de correction est ajoutée à ce moment-là.

---

## Tâche 1 : Établir la baseline (les tests passent sur les versions actuelles)

**Fichiers :** (lecture seule)

- [ ] **Étape 1 : Lancer la suite de tests complète sur les versions actuelles**

```bash
python -m pytest tests/ -v
```

Attendu : tous les tests passent. Si des tests échouent avant la mise à jour, stop — les corriger séparément d'abord.

- [ ] **Étape 2 : Enregistrer les versions installées pour le message de commit**

```bash
pip show click-extra rich rich-click | grep -E "Name:|Version:"
```

Sortie attendue (actuelle) :
```
Name: click-extra
Version: 7.16.1
Name: rich
Version: 13.9.4
Name: rich-click
Version: 1.9.7
```

---

## Tâche 2 : Mettre à jour les contraintes de version dans pyproject.toml

**Fichiers :**
- Modifier : `pyproject.toml` lignes 12–14

Mise à jour des bornes minimales vers les versions testées, pour que `uv sync --resolution lowest` reste sur des versions connues et stables.

- [ ] **Étape 1 : Modifier les trois lignes de dépendances**

Dans `pyproject.toml`, remplacer :

```toml
    "click-extra>=7.16.1,<8.0.0",
    "rich>=13.0",
    "rich-click>=1.9.7,<2.0.0",
```

par :

```toml
    "click-extra>=7.18.0,<8.0.0",
    "rich>=15.0.0",
    "rich-click>=1.9.8,<2.0.0",
```

- [ ] **Étape 2 : Vérifier la modification**

```bash
grep -E "click-extra|rich-click|rich" pyproject.toml
```

Attendu :
```
    "click-extra>=7.18.0,<8.0.0",
    "rich>=15.0.0",
    "rich-click>=1.9.8,<2.0.0",
```

---

## Tâche 3 : Installer les dépendances mises à jour

**Fichiers :** `uv.lock` (régénéré automatiquement)

- [ ] **Étape 1 : Synchroniser avec les nouvelles contraintes**

```bash
uv sync --extra dev,docs
```

Attendu : uv résout et installe click-extra 7.18.0, rich 15.0.0, rich-click 1.9.8, et click 8.4.1 (transitif). Aucune erreur.

- [ ] **Étape 2 : Confirmer les versions installées**

```bash
pip show click-extra rich rich-click click | grep -E "Name:|Version:"
```

Attendu :
```
Name: click
Version: 8.4.1
Name: click-extra
Version: 7.18.0
Name: rich
Version: 15.0.0
Name: rich-click
Version: 1.9.8
```

---

## Tâche 4 : Lancer la suite de tests complète sur les nouvelles versions

**Fichiers :** (lecture seule)

- [ ] **Étape 1 : Lancer tous les tests**

```bash
python -m pytest tests/ -v
```

Attendu : tous les tests passent, couverture ≥80%.

Si un test échoue → aller à la Tâche 5. Si tout passe → aller directement à la Tâche 6.

---

## Tâche 5 : Corriger les échecs de tests (conditionnelle — uniquement si la Tâche 4 a des échecs)

Sauter entièrement si la Tâche 4 passe.

Catégories d'échecs probables et corrections :

**A. Test qui vérifie le rendu exact d'un `Panel`**

Cause : rich 14.1.0 a corrigé le style du fond du titre des `Panel` — la sortie rendue peut différer.

Correction : mettre à jour la chaîne attendue dans l'assertion pour correspondre à la nouvelle sortie (correcte).

Motif à rechercher :
```bash
grep -rn "Panel\|panel" tests/ | grep -i "assert\|expect"
```

**B. Test qui vérifie `click.UsageError` depuis `help` sur une sous-commande inconnue**

Cause : click-extra 7.17.0 a changé `HelpCommand` pour lever `click.NoSuchCommand` au lieu de `click.UsageError`.

Correction :
```python
# Avant
with pytest.raises(click.UsageError, match="No such command"):

# Après
with pytest.raises(click.exceptions.NoSuchCommand, match="..."):
```

**C. Test qui vérifie `ValueError` au chargement de `--config`**

Cause : click-extra 7.18.0 a changé les erreurs de chargement de config de `ValueError` en `SystemExit`.

Correction :
```python
# Avant
with pytest.raises(ValueError, match="..."):

# Après
with pytest.raises(SystemExit):
```

Après chaque correction :
```bash
python -m pytest tests/ -v
```

Lancer ruff avant de committer :
```bash
ruff check src/ tests/
ruff format src/ tests/
```

---

## Tâche 6 : Vérification du linting

- [ ] **Étape 1 : Lancer ruff**

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Attendu : aucune erreur, aucun reformatage nécessaire.

---

## Tâche 7 : Commit

- [ ] **Étape 1 : Stager les fichiers modifiés**

```bash
git add pyproject.toml uv.lock
# Si la Tâche 5 a tourné, ajouter aussi : git add <fichiers de tests corrigés>
```

- [ ] **Étape 2 : Créer le commit**

```bash
git commit -m "$(cat <<'EOF'
🔧 chore(deps): upgrade click-extra, rich, rich-click

- click-extra 7.16.1 → 7.18.0 (tire Click 8.3.3 → 8.4.1 transitivement)
- rich 13.9.4 → 15.0.0 (abandonne Python 3.8 ; pyclif requiert 3.10+)
- rich-click 1.9.7 → 1.9.8 (corrige la régression de compatibilité Click 8.4.x)
EOF
)"
```

---

## Checklist de relecture

- [x] Les trois packages couverts avec des numéros de version précis
- [x] Breaking changes recherchés et mappés sur la surface de pyclif
- [x] Upgrade couplé (click-extra + rich-click + montée Click transitive) documenté
- [x] Tâche de correction conditionnelle (Tâche 5) couvre les trois catégories d'échecs les plus probables
- [x] Aucun placeholder — chaque étape a des commandes exactes et une sortie attendue
- [x] Message de commit respecte le format du projet défini dans `.claude/CLAUDE.md`