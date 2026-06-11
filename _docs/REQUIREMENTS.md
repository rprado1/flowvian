# Fase 1

- Requiero crear una aplicación que me permita crear workflows empaquetados en .exe de windows
- Debe tener una interfaz web
- Debe ser en python
- No debe usar librerias pesadas, usar en lo que se puede funciones propias de python
- La idea es que el empaquetado sea ligero
- La interfaz para crear el workflow debe ser similar al de n8n pero sin todas las funcionalidades
- Para el inicio tendra dos nodos: scheduler, set variables, get current date utc
- La base de datos debe ser sqlite
- Cada workflow debe tener un boton para generar el .exe
- Por el momento no existen sub-wokflows
- La configuracion o nodes vistos en el portal debe ser en en empaquetado transformado a codigo python y con pyinstaller crear el .exe
- Cada workflow tendra su pripia archjvo sqlite

# Fase 2

- Necesito agregar un nuevo nodo que me permita agregar (dias, horas, minutos, segundos) una fecha a otra ya generada dentro del wokflow
- Necesito agregar un nuevo nodo que me permita restar (dias, horas, minutos, segundos) una fecha a otra ya generada dentro del wokflow
