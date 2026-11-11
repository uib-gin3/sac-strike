This is an assignment from the university covering the subject 21794 - Sistemes Actuals de Computació at the University of the Balearic Islands.

You can find the syllabus at https://academic.uib.es/doa/consultaPublica/look%5bconpub%5dMostrarPubGuiaDocAs?entradaPublica=true&idiomaPais=es.ES&_anoAcademico=2026&_codAsignatura=21794

I've already done two other assignments that you'll find at /home/bartomeu/src/gin3-2026-27/sac-sock-calc and /home/bartomeu/src/gin3-2026-27/sac-restad. I want you to follow that style.

You'll find the assignment in the README in Spanish. Please translate it to English and complete it.

I would like you to implement it with the following in mind:

- Use Docker and Docker Compose to start the containers.
- Be minimalist and effective. Since this is educational, I want everything to be simple, effective, and pedagogical.
- Use /home/bartomeu/src/gin3-2026-27/sac-restad as the calculator and spawn 5 instances.
- Deploy them using Redis mode.
- Some adjustments need to be made to sac-restad. Please make these changes in the other repository. Assume that this repository will clone and use it.
- sac-restad will serve as the calculator part, and this repository, sac-strike, will handle the orchestration using Docker, etc.

I think the following changes will be needed in sac-restad:

- For this assignment, the leader has to delegate calculations to others.
- In each function of sac-restad, a node has to decide whether to perform the operation itself or delegate it.
- Use a decorator or clean Python code to implement this delegation function so the codebase remains clean.
- Use etcd to let nodes know if they are the leader. Non-leader nodes should always perform the operation and respond unless they are on strike.
- Add a header containing the hostname of the responding node.
- The leader must keep track of which node responded, how much time it took, and whether the operation failed. This information must be stored in Redis and used to determine where to delegate future requests.
- The probability of the leader performing the request itself instead of delegating must be controlled by LEADING_OVERHEAD. The probability of doing the request will be 1/number_of_colleagues - (1/number_of_colleagues * LEADING_OVERHEAD). For example, if there are 5 instances (including the leader) and a leading overhead of 10% (0.1), it would be 1/5 - (1/5 * 0.1) = 0.18 (18%).
- Implement 3 delegation algorithms:
-     Robust: Sends the request to the backend with the fewest failures.
-     Fastest: Sends the request to the backend that answers fastest.
-     Random: Sends the request to a random backend.
- An environment variable called COLLEAGUES will be sent to each sac-restad instance. It will contain a comma-separated list of the HTTP endpoints of the other backends. All servers receive the same list of colleagues, but the leader excludes itself from the list when delegating.
- If the leader delegates to a backend that fails, it will retry up to 5 times, choosing a different backend each time.
- Implement the /strike endpoint. When a sac-restad instance is struck, it will answer with 418 I'm a teapot for a random period defined by the environment variables STRIKE_MIN_TIME and STRIKE_MAX_TIME.
- Implement a /health endpoint to check if the backend is healthy (e.g., not striking, not burned out, not down).
- The sac-restad code must be compatible of what was doing so if no envvars are set sac-restad will still behave at it was.

When a node becomes the leader, a countdown is started. It will last for a random time between BURNOUT_MIN_TIME and BURNOUT_MAX_TIME. After this time, the node will also return a 418 status code, just like in a strike, so it won't be healty. 

You must use etcd to identify if the leader node is healthy and to elect a new leader if it fails.

All the enviroment variables must start with STRIKE_ (if they already have STRIKE_ there is no need to repeat it)

Implement some workload to send and see what happens.

Implement a caos monkey putting the nodes randomly on strike.

Make an script that executes everything and tells what is happening like:

- Stariting 5 nodes
- Sending X load
- We see node N is elected leader
- Caos monkey is setting Nx node into strike
- ...

The full script must be about 1 minute of tests

Show a summary of what happened and the statistics at the end. Remember that redis stores metrics of who dit what etc.

