# PyMicroscope — Instructions de travail

## Environnement de développement

- **Repo local** : `/Users/justinemajor/git/maitrise/PyMicroscope` (clone GitHub sur Mac de l'utilisatrice)
- **Machine d'exécution/tests** : `dcclab@dcc-video-2p.local` (Mac sous **Mavericks 10.9.5**, Darwin 13.4)
  - C'est là qu'est branché le matériel Epiphan
  - Le code n'a de sens que sur cette machine
- **Repo distant canonique** : `/Users/dcclab/GitHub/PyMicroscope`
  - Toujours utiliser **uniquement** ce chemin
  - Ignorer les autres copies présentes sur `dcc-video` (`~/PyMicroscope`, `~/Desktop/PyMicroscope`, `~/Documents/dccote-epiphan-dev/PyMicroscope`, etc.)

## SSH

- **Alias configuré** : `dcc-video` (dans `~/.ssh/config` local)
- **Clé** : `~/.ssh/id_rsa_dcclab` (RSA 4096, sans passphrase). Pas ed25519 — OpenSSH 6.2 sur Mavericks ne le supporte pas.
- **Algorithmes legacy** activés dans la config SSH (KEX `dh-group1/14-sha1`, `ssh-rsa`, `aes*-cbc`, `hmac-sha1`) — indispensables pour Mavericks.
- **Auth par clé** déjà installée (clé publique copiée le 2026-05-06).
- Usage : `ssh dcc-video "..."` se connecte sans mot de passe.

## Règles de travail

### Tests Epiphan → toujours en remote
**Tout code touchant à Epiphan doit être testé sur `dcc-video`, jamais en local.**

Raison : le matériel Epiphan est physiquement sur `dcc-video-2p.local`. Tester en local n'a aucune valeur (matériel absent, ou faux positif via mocks).

Avant de déclarer une tâche Epiphan terminée :
```bash
ssh dcc-video "cd ~/GitHub/PyMicroscope/tests && python3 -m unittest <module> -v"
```

Si le test ne peut pas être lancé sur `dcc-video` (réseau, repo désynchronisé, etc.), **le dire explicitement** — ne pas prétendre que le code fonctionne.

### Ne pas toucher au repo/branche local
Sauf demande explicite, **aucune modification du repo local** (`/Users/justinemajor/git/maitrise/PyMicroscope`) :
- Pas de `git checkout`, `pull`, `commit`, `push`
- Pas de `Edit`/`Write` sur les fichiers du repo
- Lecture (Read, Grep, Glob, `git status/log/diff`) : OK

Tout le travail (modifs + tests) passe par `ssh dcc-video`.

## Commandes utiles

### Synchroniser le repo distant avec une branche origin
```bash
ssh dcc-video "cd ~/GitHub/PyMicroscope && git fetch origin && git checkout <branche> && git pull --ff-only origin <branche>"
```

### Lancer les tests (le projet utilise `unittest`, pas pytest)
```bash
# Un module spécifique (depuis tests/) :
ssh dcc-video "cd ~/GitHub/PyMicroscope/tests && python3 -m unittest test_wrapper_epiphan -v"

# Toute la suite :
ssh dcc-video "cd ~/GitHub/PyMicroscope && python3 -m unittest discover -s tests"
```

Note : les tests doivent être lancés depuis `tests/` (ou avec le bon `cwd`) car ils importent `envtest` qui se trouve dans `tests/`.

### Vérifier l'état du repo distant
```bash
ssh dcc-video "cd ~/GitHub/PyMicroscope && git status && git log -1 --oneline && git branch | grep '*'"
```

### Lancer un script du package
Le package `pymicroscope` n'est pas installé sur `dcc-video` en mode dev. Toujours passer par `PYTHONPATH` et `python -m` depuis la racine du repo :

```bash
cd ~/GitHub/PyMicroscope
PYTHONPATH=src python3 -m <module.path>
```

Lancer directement `python3 fichier.py` depuis le dossier du module échoue (`ModuleNotFoundError: No module named 'pymicroscope'`) car les scripts utilisent des imports absolus.

### Lancer la GUI de diagnostic Epiphan
**Attention** : `diagnosticgui.py` n'a pas de `__main__` — c'est juste la classe `DiagnosticWindow`. Le vrai entry point est `acquisitiondaemon.py`, qui démarre Pyro + le `HardwareManager` puis ouvre la fenêtre :

```bash
cd ~/GitHub/PyMicroscope
PYTHONPATH=src python3 -m pymicroscope.acquisition.epiphan.acquisitiondaemon
```

Pour les GUI Tk, il faut être dans la session graphique locale de `dcc-video`, pas via SSH (sauf X11 forwarding).

## Particularités du projet

- **Test runner** : `unittest` (voir `run_coverage.sh`). Pytest n'est pas installé sur `dcc-video`.
- **Python distant** : `/usr/local/bin/python3` (3.11). Pas de venv. Le package `pymicroscope` n'est **pas** installé en mode dev → utiliser `PYTHONPATH=src`.
- **Helper de tests** : `tests/envtest.py` doit être importable — toujours lancer depuis `tests/`.
- **Bibliothèque Epiphan** : `src/pymicroscope/acquisition/epiphan/libfrmgrab.dylib` doit être compilée pour macOS 10.9. La branche `imageprovider_epiphan` (commit `1f681f1`) contient une version compatible ; les anciennes branches peuvent avoir une dylib qui échoue avec `load command 0x80000034 is unknown`.
- **`~/.bash_profile` sur `dcc-video`** : contient des variables TLS (`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE`) pointant vers le bundle `certifi` de Python 3.11. Nécessaire car le `curl`/`git` système de Mavericks est trop vieux pour le TLS de GitHub. Si pip casse avec `Could not find a suitable TLS CA certificate bundle`, vérifier que ces chemins existent toujours.
