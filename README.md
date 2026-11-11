# The calculators' strike

Five calculators, one leader, etcd pulling the strings, a chaos monkey and
about a minute of beautiful chaos.

- strike -> the industrial action, and also what the chaos monkey sends
  the nodes to (they answer 418 I'm a teapot while it lasts).

## Abstract

This is the orchestration half of the assignment: the calculator itself is
[sac-restad](https://github.com/uib-gin3/sac-restad), which grew a
distributed mode for the occasion. Here there is only Docker Compose to
deploy the fleet (5 calculator nodes + etcd + redis) and `strike-demo`, a
single script that starts everything, sends load to the leader, sets the
chaos monkey loose, narrates what happens and closes with a summary built
from the metrics stored in Redis.

## Assignment

Entregable: "La rebelión de las calculadoras" — translated:

> Implement at least 5 distributed entities that know how to perform
> basic mathematical operations.
>
> There must always be one acting as the leader. There will be users
> continuously sending requests to the leader: it serves them and
> delegates those operations to the other entities.
>
> When an entity is chosen as leader, an auto-destruction countdown
> (random time) is activated. After it fires it will not answer for a
> certain (random) time and when it recovers it will have lost its
> "leader" role.

Requirements:

> Freedom to use sockets, restful, etcd, zookeeper, ...
> Mandatory use of containers: at least one per entity.
> During a run of TotalTime_i quantify metrics: total and answered
> requests, delays, leaders, leader distribution, etc.

**Delivery**: in AD (the campus delivery system), include the link to the
(publicly accessible) repository containing the source code and the
relevant descriptions.


## Setup

Tested on Debian 13 with Docker 29.9.0 and the compose plugin. It should
just need bash, Docker, Docker Compose and python3 (stdlib only).

The nodes build from the sibling `../sac-restad` checkout, so:

    git clone https://github.com/uib-gin3/sac-restad
    git clone https://github.com/uib-gin3/sac-strike
    cd sac-strike


## Usage

The one-liner (about 1 minute of tests):

    ./strike-demo

It does everything: builds and starts the fleet, waits for the first
leader, sends load, runs the chaos monkey, narrates and prints the
summary. Useful options:

    ./strike-demo -c 5 -r 3 -d 60    # 5 clients, 3 ops/s each, 60 seconds
    ./strike-demo --skip-up          # the fleet is already running
    ./strike-demo --keep             # leave the fleet running at the end

Or the manual way:

    docker compose up -d --build     # etcd + redis + node1..node5
    curl localhost:12345/calc/...    # node1..node5 answer on 12345..12349
    docker compose down

The delegation behaviour is tuned with environment variables (see the
table in the sac-restad README), compose gives them defaults that can be
overridden, for example:

    STRIKE_ALGORITHM=robust docker compose up -d --build

### What the demo tells

    === The calculators' strike ===
    [   0.0s] starting the fleet: etcd + redis + 5 calculators (docker compose up -d --build)
    [   2.1s] waiting for the nodes to be healthy...
    [   2.9s] all 5 nodes are healthy
    [   3.4s] we see node3 is elected leader
    [   3.5s] sending load: 5 clients x 3.0 ops/s = 15.0 ops/s for 60s
    [   3.5s] the chaos monkey is loose: a strike every 4-9s
    [   7.9s] the chaos monkey sends node2 on strike (on strike for 4.3s)
    [  13.4s] we see node3 is elected leader
    [  14.2s] node3: burned out (burned out for 3.1s)
    [  14.7s] the leader (node3) is gone, electing a new one...
    [  15.2s] we see node1 is elected leader
    ...
    [  63.9s] the run is over: 873 ops served, collecting the metrics from redis

    === summary ===
    duration        : 61.4s
    offered (approx): 921 ops (5 clients x 3.0 ops/s)
    served          : 873 ops / 2612 reqs
    teapots (418)   : 21
    errors          : 4 (4xx: 0, 5xx: 3, conn: 1)
    latency         : avg=12.3ms p50=9.8ms p95=30.1ms p99=44.7ms max=101.2ms
    leader handled  : 2612 reqs (self: 491 = 18.8%, delegated: 2121 = 81.2%)
    orphans (503)   : 0
    chaos strikes   : 9

    per node (every request as the leader recorded it):
    node        ok   fail  avg_ms  strikes  burnouts  leading  leader%
    node1      174      2     8.9        2         1    21.2s    34.5%
    ...

    leader timeline:
      [   3.4s -  14.2s] node3
      [  15.2s -  30.0s] node1
      ...


## How it works

- **Leader election (etcd)**: the whole election is one key, `strike/leader`,
  holding the leader hostname and attached to a lease. Every node runs a
  campaign thread: a healthy node claims the key when it is free
  (compare-and-swap) and renews it every 0.5s while it leads. A struck or
  burned out leader deletes the key and steps down immediately, and when a
  leader simply dies the lease expires and the key vanishes: the next tick
  somebody else claims it. etcd is both the truth about who leads and the
  service discovery the workload uses to find the leader.
- **Delegation (sac-restad)**: every calculation route of sac-restad is
  wrapped in a `distributed` decorator. Non-leader nodes always compute
  themselves; the leader computes itself with probability
  `1/N - (1/N)·STRIKE_LEADING_OVERHEAD` (N = instances; 0.18 with 5 nodes
  and an overhead of 0.1) and delegates the rest, retrying up to 5 times
  with a different colleague on every failure. Three algorithms choose the
  colleague: `random`, `robust` (fewest failures) and `fastest` (lowest
  average response time).
- **Strikes and burnouts**: `POST /strike` sends a node on strike for a
  random window (`STRIKE_MIN_TIME..STRIKE_MAX_TIME`): it answers 418 I'm a
  teapot to every calculation and, if it was leading, steps down at once.
  Every newly elected leader starts a countdown of random
  `STRIKE_BURNOUT_MIN_TIME..STRIKE_BURNOUT_MAX_TIME`: when it fires the
  node also goes 418 for a window just like a strike, and it recovers as a
  plain node, having lost the leadership. `GET /health` always answers,
  with 200 or 418 and the reason in the body.
- **Metrics (redis)**: the leader records who responded, how long it took
  and whether it failed (`strike:ok:<node>`, `strike:fail:<node>`,
  `strike:time:<node>`), the totals (`strike:self`, `strike:delegated`) and
  a `strike:events` log with the elections, strikes, burnouts and
  delegation failures. The per-node counters also feed the robust and
  fastest algorithms; the event log feeds the leader timeline of the
  summary.
- **Signatures**: every response carries `X-Served-By` (the hostname of
  the node that computed) and `X-Leaded-By` (the leader that orchestrated,
  when there was one), so a delegated answer shows both actors.

The containers: one per calculator node, plus one for etcd and one for
redis. Ports on the host: nodes on 12345..12349, etcd on 2379, redis on
6379.


## Design decisions

Reusing sac-restad as the calculator (instead of writing a new one) keeps
the assignment honest: the calculator already worked, the interesting part
is what surrounds it. Its own docker-compose stays untouched; the fleet
lives here.

One etcd key and one lease are the smallest leader election that can be
explained in a sentence. Raft is inside etcd, not inside this repo.

The strike/leader state lives in the process memory, so the gunicorn
deployment is one worker with 8 threads (`--workers 1 --threads 8`)
instead of four sync workers: same API, state that does not need
synchronising inside the container.

Sessions were already in shared Redis, so a delegated `POST /calc` can
land on any node: there is no affinity to break.

The workload does not retry: a teapot during a leadership transition is
honestly counted, which is exactly what the assignment wants to see
(requests offered versus answered).

The chaos monkey only strikes. Killing containers would be a nice extra,
but strikes already trigger step-downs and re-elections, which is the
interesting part.


## Observations

The demo is deterministic-ish in its drama: with the default 2-6s strikes
every 4-9s and 8-20s burnout countdowns, expect roughly one leadership
transition every ~10s and a node on strike ~25% of the time. The 5-retry
delegation absorbs most of it: the summary usually shows a handful of
teapots (the seconds where the old leader answers 418 before etcd has a
new leader) and very few 5xx.

The delegation algorithm changes the failure profile of the same 30s run
(same chaos, ~1300 requests):

| algorithm | per-node failures | what happens |
|-----------|------------------:|--------------|
| random    | ~80 per struck node | spreads the damage around |
| robust    | ~1-4 per node | stops delegating to whoever fails, the struck node starves |
| fastest   | up to 240 on one node | concentrates on the historically quickest node, even while it is on strike: its success-only average looks great |

`fastest` reads averages of successful answers, so a node that is quick
when up stays attractive while it is down and the retries pay the bill.
Robust is the boring one that never hurts the clients; random is the
fair one. Pick your poison with STRIKE_ALGORITHM.

See the sac-restad README for the calculator side.


## AI usage

None of the text intended to be read by a human has been generated by an
AI tool, whereas most of the text (code) intended to be processed by a
machine has been generated by AI Agents (OpenCode).

This approach is to avoid being a [meat proxy](https://gruhn.me/blog/2026-08-03/).

- GLM-5.3-Flash (opencode): Plan and implement the whole sac-strike
  assignment (etcdapi.py, the strike mode of app.py, docker-compose.yml,
  strike-demo and the READMEs of both repositories)
- MiniMax-M3.1-Flash (opencode): sac-restad itself (see its README)
