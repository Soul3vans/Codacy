# Codacy
**(0)** 
Primero es lo Primero tienes que descargar el repo
git clone https://github.com/Soul3vans/Codacy.git

**(1)**
Luego tienes que crear un entorno virtual
python -m venv venv
source venv/bin/activate

**(2)**
Luego tienes que instalar unas cositas
pip install pip-compile-multi
pip install -r requirements/base.txt

**(3)**
Crea y actualiza las tablas y haste suprusuario
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

**(4)**
Ya puedes hechar a andar el servidor
python manage.py runserver

**(5)**
Aunque el proyecto sea funcional por ahora todavia no cumple las espectativas del cliente. OJO faltan algunos detalles.


