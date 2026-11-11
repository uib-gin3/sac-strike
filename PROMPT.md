This is an assignment from the univeristy covering the subject 21794 - Sistemes Actuals de Computació. of university of the Balearic islands.

You can find the syllabus at https://academic.uib.es/doa/consultaPublica/look%5bconpub%5dMostrarPubGuiaDocAs?entradaPublica=true&idiomaPais=es.ES&_anoAcademico=2026&_codAsignatura=21794

I've already did two other assignments that you'll find at /home/bartomeu/src/gin3-2026-27/sac-sock-calc /home/bartomeu/src/gin3-2026-27/sac-restad. I want you to follow that style.

You'll find the assingment in the README in spanish, translate it to english and do it.

I would like you to implement with this in mind:

- Use docker and docker compose to start the containers
- Be minimalist and effective, this is educational i want to be everything simple, efective and pedagogic
- Use /home/bartomeu/src/gin3-2026-27/sac-restad as the calculator, spawn 5 of them
- Deploy them with the redis mode.
- Some adjustments to sac-restad have to be made do the changes on the other repo. Assume that this repo will clone it and use it.
- sac-restad will be the calculator part and this repo sac-strike the orchestraton with the dockers etc.
- I think those changes will be needed at sac-restad:
    - For this assigment the leader have to delegate calculus to others
    - On each funcion of sac-restad a node have to decide if they do the operation or if they delegate.
    - Use some kind of decorator or python nice clean code to do that so the code stays clean while this delegation function is implemented
    - Use etcd to let them know if they are a leader or not. If they are not a leader they always do the opearton and respond.
    - Add a header adding the hostname of who responded.
    - The leader must keep track of who responded and how much time it took. This information must be kept in the redis and will be used to knwo who delegate to. Also if the operation had failed.
    - The probability of the leader being the one actually doing the request instead of delegation must be controled by LEADING_OVERHEAD. The proability of doint the request will be 1/number_of_colleages - 1/number_of_colleages x LEADING_OVERHEAD. So fi there are 5 instances (incuding the leader) and a leadig overhead of 10% (0.1) it would be 1/5 -1/5x0.1 =  0.18 (18%)

    - Implement 3 delegation algorithms:
        - robust: sending the request to the backend that failed less
        - fastest: sendinf the request to the backend that answer faster
        - random: just send the request to a random one
    - A enviroment variable will be send to each sac-restad called STRIKE_COLLEGUES= with comma separated list of the http endpoints of the other backents. All the server receives the same collegues but the leader exudes himself from the list to delegate.
    - If the leader delegats to a backend that fails it will retry to another backend up to 5 times changing the backend each time.
    - Implement the endpoint /strike, when a sac-restad is striked it will be answering 418 I'm a teapod for a random period of time defined in envvar STRIKE_MIN_TIME,STRIKE_MAX_TIME
    - Implement a /health to know if the backend is healty (not striking, not burnout) not down etc.
    - When someone becamkes a leader also a countdown is started, It will be a random time betewn STRIKE_BURNOTU_MIN_TIME,STRIKE_BURNOUT_MAX_TIME and also will returns 418 like in strike.
- Use etcd must identify if the node is healty and elect new leader.
