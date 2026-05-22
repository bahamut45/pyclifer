# How-to Guides — spec

Section à ajouter à la documentation MkDocs sous `docs/how-to/`.

## Sujets à couvrir

- Interface simple → commande construit le `Response`
- Interface avec rendu Rich progressif (live table, spinners) → retourne `Response` directement
- Commandes qui coordonnent plusieurs intégrations via le contexte
- Gestion d'erreurs avec `Response(success=False, error_code=...)`
- Utilisation de `--output-format` selon le contexte (json pour scripts, rich pour interactif)

## Intégration MkDocs

Ajouter dans `mkdocs.yml` nav :

```yaml
- How-to Guides:
    - how-to/index.md
    - how-to/response-patterns.md
    - how-to/rich-progressive-output.md
    - how-to/multi-integration-commands.md
    - how-to/error-handling.md
    - how-to/output-format.md
```