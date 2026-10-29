CREATE SUBSCRIPTION travel_sub 
CONNECTION 'host=postgres port=5432 dbname=traveler_prod user=repuser password=rep_password' 
PUBLICATION travel_pub;