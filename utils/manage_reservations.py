import json
import os
from .manage_restaurant import get_restaurant_by_name

all_reservations = []
async def add_reservation(name_restaurant: str, date_reservation: str, user_id: int):
    if not get_restaurant_by_name(name_restaurant):
        return False, "Le restaurant n'existe pas."

    if user_id in [res['user_id'] for res in all_reservations if res['name_restaurant'] == name_restaurant and res['date_reservation'] == date_reservation]:
        return False, "Vous avez déjà une réservation pour ce restaurant à cette date."

    user_reservations_count = sum(1 for res in all_reservations if res['user_id'] == user_id and res['name_restaurant'] == name_restaurant and res['date_reservation'] == date_reservation)
    if user_reservations_count >= 5:
        return False, "Vous avez atteint le nombre maximum de réservations pour ce restaurant à cette date."

    all_reservations.append({
        "name_restaurant": name_restaurant,
        "date_reservation": date_reservation,
        "user_id": user_id
    })

    await save_reservations_to_file()

    return True, "Réservation ajoutée avec succès."

async def get_all_reservations():
    global all_reservations
    if all_reservations:
        return all_reservations

    path = os.path.join(os.path.dirname(__file__), "..\\data")
    if not os.path.exists(path):
        os.makedirs(path)

    if not os.path.exists("data/reservations.json"):
        return []

    try:
        with open("data/reservations.json", "r") as file:
            all_reservations = json.load(file)
            return all_reservations
    except json.JSONDecodeError:
        return []

async def get_all_reservations_by_restaurant(name_restaurant: str):
    reservations = await get_all_reservations()
    restaurant_reservations = [res for res in reservations if res['name_restaurant'] == name_restaurant]
    return restaurant_reservations

async def remove_reservation(name_restaurant: str, date_reservation: str, user_id: int):
    global all_reservations
    all_reservations = await get_all_reservations()
    reservation_to_remove = next((res for res in all_reservations if res['name_restaurant'] == name_restaurant and res['date_reservation'] == date_reservation and res['user_id'] == user_id), None)
    if reservation_to_remove:
        all_reservations.remove(reservation_to_remove)
        await save_reservations_to_file()
        return True, "Réservation supprimée avec succès."
    else:
        return False, "Aucune réservation trouvée pour ce restaurant à cette date pour cet utilisateur."

async def save_reservations_to_file():
    with open("data/reservations.json", "w") as file:
        json.dump(all_reservations, file, indent=4)

async def get_reservations_by_user(user_id: int, name_restaurant: str = None):
    reservations = await get_all_reservations()
    user_reservations = [res for res in reservations if res['user_id'] == user_id and (name_restaurant is None or res['name_restaurant'] == name_restaurant)]
    return user_reservations