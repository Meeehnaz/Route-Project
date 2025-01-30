import os
import pandas as pd
from django.core.wsgi import get_wsgi_application
from spotter_lab.models import FuelStation 

# Setting up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_project.settings")
application = get_wsgi_application()

def load_fuel_data():
    df = pd.read_csv("fuel_stops.csv") 

    for _, row in df.iterrows():
        FuelStation.objects.update_or_create(
            opis_id=row["OPIS Truckstop ID"],
            defaults={
                "name": row["Truckstop Name"],
                "address": row["Address"],
                "city": row["City"],
                "state": row["State"],
                "rack_id": row.get("Rack ID", None),  
                "price": row["Price"],
                "latitude": row["Latitude"],
                "longitude": row["Longitude"],
            }
        )

    print("Fuel data loaded successfully!")

if __name__ == "__main__":
    load_fuel_data()
