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
- 4. Requiero que el node set variables, tambien permita definir valores para cada key del input en base a ${variable name} similar al node http get, ademas en el node set variables, los inputs deben estar uno por cada lienea, actualmente esta [Input key] [Select type] [Input value], debe ser [Input key] <br> [Select type] <br> [Input value]
- 5.- Ahora, si en el node set variables el input es un object, por ejemplo {'args': {'country': 'EC'}}, quiero que al definir una varaible, me permitea seleccionra un item dentro dese objecto por ejemplo args
- 6.- Requiero implemental el nodo if, debe tener un input en donde ingresara una varible del flujo en formato ${VARIABLE} un selector de la condicion a evaluar y otro input para ingresar un valor o variable a compara, considerar que los tipos de datos a comparar: string, number, boolean, object y array, por lo ntanto existen diferentes comparaciones dependiendo del tipo por ejmplo
- 7.- Requiero implementar el nodo Stop and Error
- 8.- Requiero implementar el nodo Split, que permite ingresar una variable en el formato ${VARIABLE} que debe ser del tipo array, y los separa en varios items dentro del flujo, debe tener la opcion Include Other Input Fields para cada nuevo item
- 9.- Revisar y proponer opciones para mejorar el UX del menu de seleccion de nodos, ya que actualmente hay muchos nodos y la seccion donde se eligen se esta quedando pequena.
- 10.- Requiero crear el node Filter node, similar a If node, solo que este nuevo nodo no tienen dos salidas, solo una, los items filtrados
- 11.- Reguiero implemtnar el nodo Aggregate, que es el nod contrario a Split, el nodo agrega en una sola lista todos los items con todos sus campos
- 12.- Requiero implementar un nodo para formatear una fecha, debe haber un campo para declarar una variable dentro del flujo ${VARIABLE}, un selector de formatos de fechas entro ellos Unix Ms Timestamp y un campo para definir el nombre de la variable con la fecha con formato, debe tener tambien tener el campo Include Other Input Fields
- 13.- Requiero tener un nodo Sort que me permita ordena la lista del flujo de forma asc o desc de acuerdo a un campo
- 14.- Requier crear un nodo Switch, similar al nodo if, solo que para cada condicion se considera una ruta de salida, solo los items del flujo quen concida con la condición iran a la ruta

# Fase 4

- 1.- Requier una forma de almacenar secretos para mi ejecutable, cada workspace debe tener una pagina en donde se guarden secretos (key, value), se debe usar una base de datos sqlite, los valores value de la tabla deben estar encriptados, al crear un workspace se crea la base de datos y la tabla para guardar los secretos, se requiere una interfaz crud para guardar los secretos, en el portal los secretos se ofuscan, no deben verse, reemplazar por asteriscos
- 2.- Requiero ahora implementar un nodo que me permite configurar https://developers.openai.com/api/reference/resources/responses/methods/create, los parametros debe ser los minimos para que finciones, los requeridos son base_url, api_key, model, message (Ejemplo input=[
  {
  "role": "system",
  "content": "You are a helpful math tutor. Guide the user through the solution step by step.",
  },
  {"role": "user", "content": "how can I solve 8x + 7 = -23"},
  ]), instructions, temperature
