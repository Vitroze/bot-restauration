# Config
## add_restaurant (Perm : admin)
> Ajoute un restaurant à la liste des restaurants.

Args :
- `name` : Le nom du restaurant à ajouter.
- `description` : Une description du restaurant.
- `location:optional` : L'emplacement du restaurant (optionnel).

## remove_restaurant (Perm : admin)
> Supprime un restaurant de la liste des restaurants.

Args :
- `name` : Le nom du restaurant à supprimer.

## edit_restaurant (Perm : admin & owner_restaurant)
> Modifie les informations d'un restaurant existant.

Args :
- `name` : Le nom du restaurant à modifier.
- `description:optional` : Une description du restaurant (optionnel).
- `location:optional` : L'emplacement du restaurant (optionnel).

## modify_role_restaurant (Perm : admin)
> Modifie le rôle associé au restaurant