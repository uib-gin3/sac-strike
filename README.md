# Assignment

Entregable

``La rebelión de las calculadoras’’

    Implementa mínimo 5 entidades distribuidas que sepán realizar operaciones matemáticas básicas.
    Siempre ha de haber una que sea líder.
    Habrá usuarios que pidan continuamente peticiones al líder, él le atenderá y delegará en las otras entidades ese reparto de operaciones.
    Cuando una entidad se elige como líder, se activa una cuenta atrás de autodestrucción (tiempo aleatorio). Despues de su activación no responderá durante un cierto tiempo (aleatorio) y cuando se recupere habrá perdido su role de “leader”

Requerimientos:

    Libertad para usar sockets, restful, etcd, zookeeper,…
    Obligatorio el uso de containers: mínimo uno por cada entidad.
    Durante una ejecución de Totaltimei

cuantificar métricas: peticiones totales y atendidas, demoras, lideres, distribución de lideres, etc.
