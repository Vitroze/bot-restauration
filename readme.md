# 🍔 Bot Restauration — Vitroze

Bot Discord de gestion complète pour restaurants : menus, réservations, commandes en salon
privé, tickets de support et système de permissions par restaurant.

## ✨ Fonctionnalités

- **Gestion des restaurants** : création, modification, suppression et catégorisation via une
  interface interactive (boutons et menus déroulants).
- **Menus interactifs** : consultation du menu avec pagination, panier, paiement via modal et
  création d'un **salon de commande privé** par client.
- **Prise en charge des commandes** : boutons dynamiques « Prendre la commande » / « Fermer la
  commande » réservés aux chefs, avec suppression automatique du salon.
- **Réservations** : réservation de table avec rappels automatiques (de 30 minutes à 2 jours
  avant la date), consultation et annulation.
- **Tickets** : module de ticket avec salon configuré et catégories par type
  (📝 Recrutement, ❓ Support).
- **Permissions par restaurant** : grille de 9 permissions accordées par rôle (ou par
  utilisateur), vérifiées sur les commandes **et** sur les boutons des interfaces.
- **Persistance JSON** dans le dossier `data/` (aucune base de données requise).

## 🚀 Installation

### Prérequis

- Python **3.11+**
- Un token Discord ([Portail développeur Discord](https://discord.com/developers/applications))

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/Vitroze/bot-restauration.git
cd bot-restauration

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer le fichier .env à la racine
echo DISCORD_TOKEN=votre_token > .env

# 4. Lancer le bot
python main.py
```

`.env` :

```env
DISCORD_TOKEN=xxx
```

> Les commandes slash sont synchronisées au démarrage sur le serveur de développement
> (ID `858647206394200064` — à modifier dans `main.py` si besoin).

## 📜 Commandes disponibles

### 🍽️ Restaurants & menus

| Commande | Description | Paramètres | Permission |
|---|---|---|---|
| `/menu` | Affiche le menu d'un restaurant (avec panier et paiement) | `restaurant` | Tous |
| `/profile` | Affiche le profil d'un restaurant (type, localisation) | `restaurant` | Tous |

### 📅 Réservations

| Commande | Description | Paramètres | Permission |
|---|---|---|---|
| `/reserver` | Réserver une table (formulaire : restaurant + date) | — | Tous |
| `/mes_reservations` | Affiche vos réservations à venir | — | Tous |
| `/annuler_reservation` | Annule l'une de vos réservations | `restaurant`, `date` (JJ/MM/AAAA) | Tous |
| `/restaurant_voir_reservations` | Liste les réservations d'un restaurant | `restaurant`, `user`*, `hidden`* | `see_reservations` ou admin |

\* Paramètres optionnels : `user` filtre sur un membre, `hidden` rend le message éphémère
(par défaut `True`).

> Les réservations doivent être situées entre demain et 30 jours maximum. Un rappel est envoyé
> en MP automatiquement (30 min, 1 h, 2 h, 6 h, 12 h, 1 jour, 2 jours avant).

### ⚙️ Configuration (administrateur)

| Commande | Description | Paramètres |
|---|---|---|
| `/cfg_restaurant` | Ouvre l'interface de gestion des restaurants (voir détails ci-dessous) | — |
| `/cfg_create_restaurant` | Crée un restaurant | `name`, `description`, `type_restaurant`, `location` |
| `/cfg_create_type` | Crée un type de restaurant (ex : Pizzeria) | `name` |
| `/cfg_delete_type` | Supprime un type de restaurant | `name` |
| `/cfg_channel_ticket` | Définit le salon d'envoi du panneau de tickets | `channel` |
| `/cfg_category_ticket` | Définit la catégorie où créer les tickets d'un type | `ticket_type`, `category` |

> ⚠️ La création d'un restaurant nécessite que son **type existe au préalable**
> (`/cfg_create_type`).

### 🎛️ Interface `/cfg_restaurant`

L'interface propose, pour le restaurant sélectionné :

| Bouton | Action | Permission requise |
|---|---|---|
| Sélecteur de restaurant | Ouvrir la fiche de configuration | `view_config` |
| ✏️ Modifier | Éditer nom/type/description/localisation | `edit_restaurant` |
| ➕ / ➖ Rôles | Accorder ou retirer des permissions à un rôle | `manage_permissions` |
| 🗑️ Supprimer | Suppression du restaurant (avec confirmation) | `edit_restaurant` |
| 🏷️ Catégorie | Choisir la catégorie Discord des salons de commande | `edit_restaurant` |
| 🍽️ Ajouter un item | Ajouter un plat au menu | `add_item_menu` |
| ✏️ Modifier un item | Modifier un plat du menu | `edit_item_menu` |
| 🗑️ Supprimer un item | Retirer un plat du menu | `remove_item_menu` |

### 🎫 Système de tickets

1. Configurer le salon avec `/cfg_channel_ticket` → un panneau « Système de ticket » est publié.
2. Les membres choisissent un type de ticket (📝 Recrutement ou ❓ Support).
3. Un salon privé est créé avec les permissions du membre + l'équipe.

> Les boutons des tickets restent ouverts à tous ; seuls les boutons de **commande**
> (prise en charge) sont réservés aux chefs (`take_command`).

## 🔐 Système de permissions

Chaque restaurant possède sa propre grille de permissions, accordée **par rôle** (ou
directement à un utilisateur) depuis l'interface `/cfg_restaurant` :

| Permission | Description |
|---|---|
| `view_config` | Voir la configuration du restaurant |
| `edit_restaurant` | Modifier les informations du restaurant |
| `manage_permissions` | Gérer les permissions du restaurant |
| `manage_reservations` | Gérer les réservations du restaurant |
| `see_reservations` | Voir les réservations du restaurant |
| `add_item_menu` | Ajouter un item au menu |
| `edit_item_menu` | Modifier un item du menu |
| `remove_item_menu` | Supprimer un item du menu |
| `take_command` | Prendre une commande dans le restaurant |

**Règles de vérification :**

- Les **administrateurs Discord** passent toujours les vérifications.
- La permission est acceptée si elle est accordée à **l'un des rôles** du membre, ou
  directement à son identifiant.
- Vérifiée à la fois sur les **commandes slash** (`@check_permission_restaurant`) et sur les
  **boutons des interfaces** (`@check_ui_permission` / `ensure_ui_permission`).
- Tout refus renvoie un message éphémère indiquant la permission manquante.

## 🛒 Parcours d'une commande

1. Un client consulte `/menu` et remplit son **panier**.
2. Il clique sur **Payer** → modal (nom, lieu, remarque) → un **salon privé**
   `commande-<utilisateur>` est créé dans la catégorie du restaurant.
3. Les chefs (`take_command`) sont mentionnés avec un récapitulatif embed.
4. Un chef clique sur **Prendre la commande** (bouton dynamique) → confirmation au client.
5. **Fermer la commande** → le salon est supprimé après 10 secondes.

## 📁 Structure du projet

```
bot-restauration/
├── main.py                  # Point d'entrée, chargement des extensions
├── commands/                # Cogs (commandes slash)
│   ├── config.py            #   Configuration des restaurants (cfg_*)
│   ├── menu.py              #   /menu et /profile
│   ├── reservation.py       #   Réservations
│   └── ticket.py            #   Cog ticket (en cours)
├── models/
│   ├── restaurant.py        # Modèle Restaurant / RestaurantType
│   └── rappels.py           # Boucle de rappels de réservation
├── ui/                      # Vues Discord (boutons, modals, embeds)
│   ├── base_view.py         #   BaseView / PaginatedView (auteur + timeout)
│   ├── config_restaurant.py #   Interface de gestion des restaurants
│   ├── menu.py, checkout.py #   Menu, panier et paiement
│   ├── order_ticket.py      #   Boutons de prise en charge des commandes
│   └── ...                  #   Édition items, permissions, catégorie, réservations
├── utils/
│   ├── manage_restaurant.py #   CRUD restaurants (JSON)
│   ├── manage_reservations.py
│   ├── manage_ticket.py     #   Système de tickets
│   ├── manage_permission.py #   Vérification des permissions
│   ├── logger.py            #   Logs colorés en console
│   └── function_utils.py    #   Utilitaires (prix, rôles chefs…)
└── data/                    # Stockage JSON (généré automatiquement)
    ├── restaurants.json
    ├── restaurant_types.json
    ├── reservations.json
    └── config.json
```

## 🛠️ Développement

### Dépendances

```
discord.py>=2.3
python-dotenv>=1.0
```

### Qualité de code

Le projet est configuré selon **PEP 8** (max 100 caractères par ligne) :

```bash
pip install black flake8 isort
black .            # Formatage
isort .            # Tri des imports
flake8 .           # Vérification (0 violation attendue)
```

Configuration centralisée dans `.flake8` et `pyproject.toml`.

### Consignes du projet

- Commenter « un peu » le code.
- **Maximum 300 lignes** par fichier Python.
- Stocker les données dans des **fichiers JSON**.

