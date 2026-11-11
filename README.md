# The calculators' strike

Five calculators, one leader, etcd pulling the strings, a chaos monkey and
about a minute of beautiful chaos.

- strike -> the industrial action, and also what the chaos monkey sends
  the nodes to (they answer 418 I'm a teapot while it lasts).

## Abstract

This is the orchestration half of the assignment: the calculator itself is
[sac-restad](https://github.com/uib-gin3/sac-restad), which grew a
distributed mode for the occasion. Here there is only Docker Compose to
deploy the workforce (5 calculator nodes + etcd + redis) and a handful of
single-purpose commands (strike-up, strike-leader, strike-load,
strike-chaos, strike-watch, strike-summary) that `strike-demo` composes
into the whole show: start everything, send load to the leader, set the
chaos monkey loose, narrate what happens and close with the reports
built from what the clients saw and from the metrics stored in Redis.

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

It composes the single-purpose commands: brings the workforce up, waits
for the first leader, runs the chaos monkey and the storyteller in the
background, sends load in the foreground, prints the two reports and
tears the workforce down. Useful options:

    ./strike-demo -c 5 -r 3 -d 60    # 5 clients, 3 ops/s each, 60 seconds
    ./strike-demo --skip-up          # the workforce is already running
    ./strike-demo --keep             # leave the workforce running at the end

### The commands, one thing each

Unix style: every tool is useful on its own, open a few terminals and
mix them as you like.

    ./strike-up                      # workforce up, healthy, leader elected
    ./strike-leader                  # where to send requests: the leader's base URL
    ./strike-load -c 5 -r 3 -d 60    # the users: load and the client report
    ./strike-chaos -d 60             # the agitator: random strikes
    ./strike-watch                   # the storyteller: narrates forever
    ./strike-summary -d 60           # the ledger: what redis recorded
    ./strike-client -o add 3 4 5     # one operation, leader auto-discovered
    docker compose down

They share one clock: strike-demo exports `STRIKE_T0` and every tool
narrates `[xx.xs]` on the same timeline (standalone, they clock
themselves). strike-load keeps its simulated users as internal threads,
just like restad-bench does.

### Always send the request to the leader

etcd holds the leadership in the `strike/leader` key, with the endpoint
of the leader, so asking etcd is enough:

    docker compose exec etcd etcdctl get strike/leader --print-value-only
    # http://node2:12345

`strike-leader` turns that into a base URL for the host (the compose
maps nodeN to 12345+N-1) and retries the sub-second gaps. Inline the
discovery in every command: if the leader changes (or dies) between
commands, each one finds whoever leads at that moment, and the calculus
survives it anyway (sessions live in shared redis, any node can serve
any calculus):

    ID=$(curl -s -X POST $(./strike-leader)/calc --data-binary 3,4,5,6)
    curl -v $(./strike-leader)/calc/$ID/add
    # X-Lead-By: node2         the leader that orchestrated
    # X-Calculated-By: node5   the node that computed
    # 18

    ./strike-leader --endpoint     # the raw endpoint etcd holds

Or without curl at all, with the discovery built in:

    ./strike-client -o add 3 4 5
    ./strike-client -o mean 1 2 3 4
    ./strike-client -v -o sqrt 49

The leader is always there, even on a workforce nobody is talking to: a
guardian thread in every node repeats the keepalive pass every TTL/3,
so memberships stay fresh, the leadership is renewed (or claimed by the
next node when the leader dies or burns out) and the burnout countdowns
fire on time with zero traffic. Watch it churn:

    watch -n 1 'docker compose exec etcd etcdctl get strike/leader --print-value-only'

Only the sub-second gaps between a lease expiring and the next claim
are leaderless; strike-leader and strike-client retry them for you.

The delegation behaviour is tuned with environment variables (see the
table in the sac-restad README), compose gives them defaults that can be
overridden, for example:

    STRIKE_ALGORITHM=robust docker compose up -d --build

There is no colleague list to configure: every node registers itself in
etcd and the workforce is whatever etcd says it is.

### What the demo tells

    === The calculators' strike ===
    [   0.0s] starting the workforce: etcd + redis + 5 calculators (docker compose up -d --build)
    [   4.3s] waiting for the nodes to be healthy...
    [   5.9s] all 5 nodes are healthy
    [   5.9s] we see node1 is elected leader
    [   6.0s] the chaos monkey is loose: a strike every 4-9s
    [   6.0s] sending load: 5 clients x 3.0 ops/s each (total 15.0 ops/s) for 60s
    [  11.0s]   77 ops in  5.0s (  15.4 ops/s) reqs=231 teapots=0 errors=0
    [  14.4s] the chaos monkey sends node1 on strike (on strike for 2.3s)
    [  14.8s] the leader (node1) is gone, electing a new one...
    [  15.3s] we see node2 is elected leader
    [  28.3s] node2: burned out (burned out for 2.5s)
    [  28.9s] we see node1 is elected leader
    ...
    [  64.5s] the storyteller goes home
    [  64.7s] the chaos monkey is done: 8 strikes

    === what the clients saw ===
    duration        : 60.0s
    offered (approx): 901 ops (5 clients x 3.0 ops/s each)
    served          : 847 ops / 2556 reqs
    teapots (418)   : 15
    errors          : 0 (4xx: 0, 5xx: 0, conn: 0)
    latency         : avg=7.3ms p50=6.1ms p95=14.6ms p99=19.0ms max=27.5ms
    client view (X-Calculated-By): node1: 211, node2: 197, node3: 114, ...

    === what the workforce recorded ===
    duration        : 60.0s
    leader handled  : 2541 reqs (self: 460 = 18.1%, delegated: 2081 = 81.9%)
    orphans (503)   : 0
    strikes suffered: 8

    per node (every request as the leader recorded it):
    node        ok   fail  avg_ms  strikes  burnouts  leading  leader%
    node1      672     39     1.7        1         1    27.9s    46.5%
    node2      579     91     1.8        1         2    18.0s    30.0%
    ...

    leader timeline:
      [   5.0s -   14.4s] node1
      [  14.8s -   28.1s] node2
      ...


## How it works

- **Leader election (etcd)**: two etcd key families hold the whole shared
  state, both attached to leases. Every node registers itself under
  `strike/workforce/<hostname>` with its endpoint, and the leadership is
  the single key `strike/leader`, holding the endpoint of the leader too
  (the same format, so a client can use it as its base URL). Requests
  drive the decisions: every request runs one keepalive pass that
  re-asserts membership and asks etcd who leads; a leaderless workforce
  elects a leader on the next pass (compare-and-swap), the leader renews
  its lease while requests come, a struck or burned out leader steps
  down the moment a pass finds it, and if a leader simply dies its lease
  expires and the next pass elects somebody else. And because silence
  kills leases, every node also runs a guardian thread repeating the
  same pass every TTL/3: the state in etcd never goes dark, there is
  (almost) always a leader even when nobody is talking to the workforce,
  and the burnout countdowns fire on time. A quiet node never drops out
  of the delegation pool anymore. etcd is both the truth about who leads
  and the service discovery the workload uses to find the leader.
- **Delegation (sac-restad)**: every calculation route of sac-restad is
  wrapped in a `distributed` decorator. Non-leader nodes always compute
  themselves; the leader computes itself with probability
  `1/N - (1/N)·STRIKE_LEADING_OVERHEAD` (N = workforce size; 0.18 with 5
  nodes and an overhead of 0.1) and delegates the rest, retrying up to 5
  times with a different colleague on every failure. Three algorithms
  choose the colleague: `random`, `robust` (fewest failures) and `fastest`
  (lowest average response time).
- **Strikes and burnouts**: `POST /strike` sends a node on strike for a
  random window (`STRIKE_MIN_TIME..STRIKE_MAX_TIME`): it answers 418 I'm a
  teapot to every calculation and, if it was leading, deletes the leader
  key right away. Every newly elected leader starts a countdown of random
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
- **Signatures**: every response carries `X-Calculated-By` (the hostname
  of the node that computed) and `X-Lead-By` (the leader that
  orchestrated, when there was one), so a delegated answer shows both
  actors.

The containers: one per calculator node, plus one for etcd and one for
redis. Ports on the host: nodes on 12345..12349, etcd on 2379, redis on
6379.


## Design decisions

Reusing sac-restad as the calculator (instead of writing a new one) keeps
the assignment honest: the calculator already worked, the interesting part
is what surrounds it. Its own docker-compose stays untouched; the workforce
lives here.

One etcd key per node (its workforce entry) plus one leader key, all with
leases, are the smallest election and service discovery that can be
explained in a sentence. Raft is inside etcd, not inside this repo.

There is no management loop doing decisions: requests run the keepalive
pass and decide from fresh etcd reads. The only background thread is
the guardian, which repeats the very same pass in the silence so the
etcd state never goes dark. The trade-off is honest: during the
sub-second gaps between a lease expiring and the next claim there is no
leader, and an etcd outage longer than two beats drops the leadership
until etcd is back. In exchange the countdowns fire by the clock, the
idle workforce keeps churning leaders like the assignment describes,
and there is always an endpoint to find at etcd.

The strike/leader state lives in the process memory, so the gunicorn
deployment is one worker with 8 threads (`--workers 1 --threads 8`)
instead of four sync workers: same API, state that does not need
synchronising inside the container.

The demo is not one program with threads for everything; it is five
single-purpose commands and a thin shell composition. Every tool is
useful alone (load in one terminal, the storyteller in another), they
share no state (the clients' report is strike-load's, the workforce's
record is strike-summary's, straight from redis) and the only thing
strike-demo adds is the order and one shared clock, `STRIKE_T0`.

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
  strike-demo and the READMEs of both repositories) also needed modificatios
  on sac-restad.
