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
- Ejecución paralela de nodos
- Requiero tern en el potal un boton run para ejcutar un workflow, al ejecutar se van ejectuando los ndos, en la parte inferior en una tabla/arbol se muestra los datos de entrada y salida de cada nod ejecutado
- 5. Requiero que los nodos tengan un nombre unico, cuando se crean tienen el mismo nombre, si se crean nuevos nodos si ya existen nombres similares agregar un sufijo numerico
- 6.- Cuando selecciono un nodo, se abre el sidebar de configuracion, si doy clic en la tecla suprimiar el nodo se elimina, pero el sidebar conrinua abierto y se bloquea no le puedo cerrar, deberia cerrarse cuando se elimina el nodo
- 7.- Requiero que el flujo de datos en cada nodo sea un array, el primer nodo debe como tener entrada [{"workflowId","executionId","executionDate"}]
- 8.- El execution id es un id random unico de ejecucion
- 9.- Cada nodo se debe ejecutar para los n items en el flujo actual
- 10.- Cada nodo con salida de datos debe tener la opción "Include Other Input Fields"
- 11.- Se requiere un nodo `merge` que implemente la estrategia `append`.
- 12.- Requier que el nodo merbe pueda concatenar n ramas, para esta en la configuracion debe tener el input con el numero de ramas a combinar

#Fase 3

- 1.- Requiero un node Wait, por segundos unicamente
- 2.- Requiero un node que me permita hacer peticiones HTTP con los metodos POST y GET, debe permitir enviar custom headers y Body raw json para POST, debe permitir usar valores dentro del flujo pra configurarlo en la URL, Headers o BOdy raw json, para llamarlso se usa ${NOMBRE_VARIABLE}
- 3.- Requiero que el node set variables me permita definir el tipo de variable: String, Number, Boolean
