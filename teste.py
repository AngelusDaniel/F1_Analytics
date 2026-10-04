from sqlalchemy import select
from projeto_f1.app.db import SessionLocal
from projeto_f1.app.models import Race, Driver

#statement = select(Race).where(Race.season == "2023").limit(10)

#with SessionLocal() as session:
#	races = session.scalars(statement).all()
#	for race in races:
#		print(race)


statement_name = select(Driver.given_name, Driver.nationality).where(Driver.nationality == "Dutch").limit(10)

with SessionLocal() as session: 
	drivers = session.execute(statement_name).all()
	for driver in drivers:
		print(driver)



