# The calculators' strike — prompt log

This file is the prompt of the assignment plus the design interactions
that shaped the final code. The idea: with this file, an empty
repository and an AI coding agent, more or less the same implementation
comes out. The interactions are on top (the latest decision wins), and
the original prompt is kept verbatim at the end.

## Original prompt

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

## Interaction 1 — title and a second header

> "Rename also the assignment to The calculators' strike instead of
> rebellion. Also add the X-Leaded-By header"

Decisions:

- The assignment is called **"The calculators' strike"** everywhere
  (README title, demo banner).
- Every response is signed with two headers:
  - `X-Served-By`: hostname of the node that computed the operation.
  - `X-Leaded-By`: hostname of the leader that orchestrated it, set by
    the leader when it serves or delegates; absent on the rare direct
    hits to non-leaders.

## Interaction 2 — the colleagues register themselves in etcd

> "I would like all the colleagues to register themselves to etcd
> instead of having an envvar. I would prefer to check etcd for things
> instead of having variables like am_leader, would not be better to
> check if I'm the leader directly to etcd, that way tick and campaign
> are less necessary?"

Decisions:

- No `COLLEAGUES` environment variable. Every node registers itself in
  etcd as `strike/workforce/<hostname>` = `http://<hostname>:<port>`
  with a TTL lease, and reads the workforce from the
  `strike/workforce/` prefix when it needs colleagues (the leader
  excludes itself). A node whose lease expires drops out of the
  delegation pool by itself.
- No cached `am_leader` shadow state: the leader check is a live etcd
  read of `strike/leader` at decision time. A short fallback cache of
  the last known workforce remains only for etcd outages.
- Graceful degradation rule: etcd unreachable → the node behaves as a
  follower (always computes locally) and never breaks a calculation.

## Interaction 3 — the workforce, fully request-driven

> "Instead of fleet name it workforce. I don't care if no leader is
> there if there is no transit. Also if the burnout appears when a
> request comes. For me is fine if requests are the ones triggering
> elections etc. Would that simplify the code?"

Decisions:

- Rename fleet to **workforce** (keys `strike/workforce/...`).
- No background thread at all. Requests (health checks included) drive
  everything:
  - every request re-asserts its node's workforce membership
    (throttled to about twice per TTL);
  - a leaderless workforce elects a leader on the next request
    (compare-and-swap on `strike/leader`);
  - the leader renews its lease while requests come (same throttle);
  - a struck or burnt out leader steps down the moment a request finds
    it, and `/strike` deletes the leader key immediately;
  - the burnout countdown is evaluated on requests: it fires on the
    first request after it expires.
- Accepted consequences: an idle workforce has no leader and
  memberships lapse; under load the leaderless gaps are milliseconds,
  so "there is always a leader" holds exactly while users are being
  served. Health checks count as requests, which is what keeps the
  workforce warm during a demo run.
- Environment variables after the refactor (all `STRIKE_` prefixed):
  `STRIKE_ETCD` (activates the mode), `STRIKE_PORT` (for the
  registration, default 12345), `STRIKE_TTL` (lease of the leader and
  workforce keys), `STRIKE_LEADING_OVERHEAD`, `STRIKE_ALGORITHM`,
  `STRIKE_MIN_TIME`, `STRIKE_MAX_TIME`, `STRIKE_BURNOUT_MIN_TIME`,
  `STRIKE_BURNOUT_MAX_TIME`, `STRIKE_RETRY`, `STRIKE_TIMEOUT`.

## Interaction 4 — the leader port in etcd

> "Can you implement that etcd also stores the leader port so its easier
> for the client to always send the request to the leader"

Decisions:

- `strike/leader` holds the full endpoint (`http://nodeN:12345`), the
  same format as the workforce entries: every etcd value is an endpoint
  now, and a client can use the value as its base URL directly.
- The nodes compare against their own registered endpoint
  (`SELF_ENDPOINT`), claim, renew and step down with it.
- `X-Leaded-By` still carries the bare hostname; `/health` prints the
  hostname.
- Host-side clients (strike-load, the manual example) still map nodeN to
  the published port 12345+N-1: the published mapping is a compose
  concern etcd should not know about.

## Interaction 5 — split strike-demo, one tool per job

> "Also separate the strike-demo into several commands that run
> separately instead of doing threads in python. I want each script to
> be responsible of one thing and do it well like the unix philosophy.
> If you need to rearchitecture how things are done at strike-demo do
> it, its important to keep everything simple and effective."

Decisions:

- One shared `strikeapi.py` module with the stdlib clients (mini RESP
  for redis, etcd v3 gateway reader, plain http helper, node/port map),
  like restadapi.py does in sac-restad.
- Five single-purpose commands, each useful alone:
  - `strike-up`: compose up, fresh redis metrics, wait for health and
    for a leader;
  - `strike-load`: the users (its simulated users are internal threads,
    like restad-bench); reports what the clients saw;
  - `strike-chaos`: the agitator, random strikes;
  - `strike-watch`: the storyteller, narrates leader changes, burnouts
    and recoveries;
  - `strike-summary`: the ledger, reads redis and reports the per-node
    table and the leader timeline.
- `strike-demo` becomes a thin shell composition (no threads): strike-up,
  then strike-chaos and strike-watch in the background, strike-load in
  the foreground, strike-summary, docker compose down.
- The tools share no state and no temp files: two honest reports, the
  clients' view is strike-load's business, the workforce's record is
  strike-summary's, straight from redis.
- One shared clock: strike-demo exports `STRIKE_T0` and every tool
  narrates `[xx.xs]` on the same timeline (standalone, they clock
  themselves).

## Interaction 6 — always a leader in etcd

> "When I've said that I didn't care about not having a leader I
> assumed that I'll always had an endpoint to send the requests. So I
> want some mechanism that is distributed and fault tolerant to keep a
> leader elected so there is always a value at etcd for the leader."

Decisions:

- A guardian thread per node repeats the exact same keepalive pass the
  requests run (`beat()`: membership + leadership dance) every TTL/3.
  Distributed (every node runs it, no coordinator), fault tolerant (a
  dead leader is detected by lease expiry in at most TTL, any healthy
  node claims on the next pass, a transient etcd hiccup is survived by
  the 2x margin), and there is no single point of failure.
- Requests remain the fast path and keep deciding from fresh etcd
  reads; the guardian only exists so the etcd state never goes dark in
  the silence: always a value at `strike/leader` (bar the sub-second
  transition gaps).
- The burnout countdown fires by the clock again, so an idle workforce
  keeps electing and burning out leaders forever, exactly as the
  assignment describes.
- An etcd outage longer than about two beats (~2.6s) drops the
  leadership; the fleet re-elects on recovery.
- Revised consequence of Interaction 3: the accepted "idle workforce
  has no leader" no longer holds; memberships never lapse either, so a
  quiet node stays in the delegation pool.

## Interaction 7 — a simpler manual example

> "In the readme there is a manual example saying: docker compose exec
> etcd etcdctl get strike/leader --print-value-only [...] LEADER=$(...)
> N=${LEADER#http://node}; PORT=$((12345 + ${N%%:*} - 1)) [...] is that
> correct? It feels unnecessary complicated"

Decisions:

- It was correct on the happy path, but the bash string surgery was
  noise in a teaching example, and it silently failed on the
  sub-second leaderless gaps: an empty LEADER made the arithmetic
  produce port 12344, where nothing listens.
- The mapping (nodeN to the published port 12345+N-1) is a job for a
  command, not for shell acrobatics: `strike-leader` answers "where do
  I send requests?" with the leader's host port (retrying the
  sub-second gaps), or with the raw endpoint under --endpoint.
- The README example is now three lines of curl and one substitution;
  the etcdctl line stays to show where the truth lives.
