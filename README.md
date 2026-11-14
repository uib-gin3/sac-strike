# The calculators' **strike**

Send calculations, and calculators will elect a leader that will lead by
example, doing the work as well as delegating part of it.

Leaders burn out so they step down and a new leader is elected.
Sometimes other calculators also step down, going on strike and having a tea.

Allegory of how IT companies work, leading usually does not relieve you of
your previous duties so you burn out. When delegating, faster workers
tend to be punished with more work and also any leader knows when
reliable work needs to be done who is the right candidate.

## Abstract

An exercise of a distributed system based on the rest calculator 
[sac-restad](https://github.com/uib-gin3/sac-restad) that has been
modified to be used also as a distributed system.

This repo [sac-strike](https://github.com/uib-gin3/sac-strike) deploys
sac-restad in a distributed way. It also includes scripts to test it, mostly
vibe-coded.

## Assignment

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
>
> Freedom to use sockets, restful, etcd, zookeeper, ...
> Mandatory use of containers: at least one per entity.
> During a run of TotalTime_i quantify metrics: total and answered
> requests, delays, leaders, leader distribution, etc.
>
> **Delivery**: in AD (the campus delivery system), include the link to the
> (publicly accessible) repository containing the source code and the
> relevant descriptions.


## Setup

Tested on Debian 13 with Docker 29.9.0 and the compose plugin. It should
just need bash, git, Docker, Docker Compose and python3 (stdlib only).

    git clone https://github.com/uib-gin3/sac-strike
    cd sac-strike

## Usage

### Full assisted test (recommended way)

There is the script `strike-demo` that runs a full demo of 1 minute.

    ./strike-demo

It composes the single-purpose commands: brings the workforce up, waits
for the first leader, runs the chaos monkey and the storyteller in the
background, sends load in the foreground, prints the two reports and
tears the workforce down.

It has interesting defaults but accepts parameters like `-c 5 -r 3 -d 60`
that would do 5 clients, 3 ops/s each, 60 seconds.


### Simple test

Start the workers (like a `docker compose up` with some asteroids)

    ./strike-up

Wait for a leader to be elected; it returns when ready

    ./strike-ready

Test a calculation: `strike-leader` returns the endpoint, then curl it.

    ID=$(curl -s -X POST $(./strike-leader)/calc --data-binary 3,4,5,6)
    curl -v $(./strike-leader)/calc/$ID/add
    # X-Lead-By: node2         the leader that orchestrated
    # X-Calculated-By: node5   the node that computed
    # 18

There is also a Python client to avoid using curl

    ./strike-client -v -o add 3 4 5 6

To know who the current leader is

    docker compose exec etcd etcdctl get strike/leader --print-value-only


### Using it manually

Unix style: every tool is useful on its own, open a few terminals and
mix them as you like.

    ./strike-up                      # start the workforce
    ./strike-ready                   # waits until a leader is elected and ready
    ./strike-leader                  # where to send requests: the leader's base URL
    ./strike-load -c 5 -r 3 -d 60    # the users: load and the client report
    ./strike-chaos -d 60             # the agitator: random strikes
    ./strike-watch                   # the storyteller: tells what is happening
    ./strike-summary -d 60           # Show what happened reading stats
    ./strike-client -o add 3 4 5     # one operation, leader auto-discovered
    docker compose down              # stops everything

They share one clock: strike-demo exports `STRIKE_T0` and every tool
narrates `[xx.xs]` on the same timeline (standalone, they clock
themselves). strike-load keeps its simulated users as internal threads,
just like restad-bench does. (This idea and paragraph were AI-generated,
I'm impressed!)

## Design decisions

Use sac-restad as a base and extend it to be usable as a distributed system
when `STRIKE_` environment variables are present, that way it is still
compatible with the previous use.

Use etcd because it is industry standard, high performance and Go-developed,
which I prefer over any clunky Java thing.

Minimizing single points of failure that a proxy would introduce,
that is why there is a script that composes the endpoint to use
(`strike-leader`) taking it from etcd (which is a SPOF itself).

As the client is not inside Docker, ports are used as the routing element so
the client can be outside Docker. On a real distributed system, DNS would be used.

Using Redis as cache, in this case it could be considered a SPOF but
it could also be deployed distributed, but I did not want to overcomplicate
the assignment with it.

Also redis is used to keep statistics.

It would have also been possible to use `etcd` as key-value storage 
and avoid using Redis but I like the idea of keeping `etcd` usage
as minimal as possible as it is critical.

It is true that there can be a gap between asking for the leader and 
sending the request. If done manually it can fail, that's why there is
`strike-client` that handles those errors and retries.

The leader does some part of the job and delegates the rest. The proportion
of how many calculations are done by the leader vs the delegated ones
is controlled by the STRIKE_LEADING_OVERHEAD envvar. The idea is to 
distribute the workload evenly across all the nodes including the leader
but as the leader has some overhead coordinating, the probability
of doing the job is reduced considering this overhead.

The formula is

    1/N - (1/N) * STRIKE_LEADING_OVERHEAD

Assuming a 10% overhead for being a leader and 5 nodes, the probability
for the leader to take a calculation would be 18% so 2% as leader job,
probably not enough, that's why they burn out ;)

How the work is delegated to the other workers is controlled by
the `STRIKE_ALGORITHM` envvar, with 3 possible algorithms:

- `random`: just as random as it sounds
- `robust`: preference for reliable workers that failed less
- `fastest`: preference for faster workers

Both `robust` and `fastest` use statistics stored in Redis to get
the values.

The nodes register themselves in etcd when starting up so the system
auto-scales. 

Leaders burn out, forcing a new leader to be elected.

Workers go on strike provoking the leader to fail and taking that into
account against their robustness, which may be relevant if it is the used algorithm.

A chaos monkey is implemented to push workers into strike.


### Leadership election with etcd

There is one key in etcd called `strike/leader`, holding the endpoint of the current
leader. It is the ZooKeeper recipe from class, with etcd playing ZooKeeper:
the key is bound to a lease with a TTL (4s by default), so it behaves like
an ephemeral node, a leader that crashes without stepping down loses the
lease, etcd deletes the key and the leadership is free again. Instead of
the ordered queue of sequential nodes and watches, a single key claimed in
a race, the losers just try again on the next beat.

Claims and renewals are compare-and-swaps. A node that finds the key free
puts its endpoint only if the key does not exist yet, so of all the nodes
racing exactly one wins. Is etcd who decides who win.

While leading, the node renews the lease every TTL/3 with a second
compare-and-swap that only succeeds while the value is still its own endpoint:
that is the heartbeat. On strike or burnout the leader deletes the key right
away; a lost renewal means another node owns the key already, so it just steps
down.

Every request runs one pass of the described system but if there are no requests
there is a thread (guardian) that keeps beating when there is no traffic, so a 
there is always an elected leader to send traffic to.

There are more details within the [app.py sourcecode of sac-restad](https://github.com/uib-gin3/sac-restad/blob/636b83c1c96410677776161b8ffce022eb82784f/app.py#L163).

## Observations

With the default 2-6s strikes every 4-9s and 8-20s burnout countdowns,
expect roughly one leadership transition every ~10s and a node on strike
~25% of the time. The 5-retry delegation absorbs most of it: the summary
usually shows a handful of teapots (the seconds where the old leader answers
418 before etcd has a new leader) and very few 5xx.

The delegation algorithm changes the failure profile of the same 30s run
(same chaos, ~1300 requests):

## Interesting future works

It would be great to play and do simulations to see which delegation algorithm
works best on different parameters and chaos situations.


## AI usage

As I had to miss some classes about the topic, I've followed a different
approach than previous assignments. In this one I've tried to prompt what
I wanted, giving the AI agent access to the lessons, and it implemented
crucial modifications to sac-restad to make it distributed, as well as configuring etcd.

The used prompts can be found in PROMPT.md

Initially this README was AI generated but I've rewritten it to be simplified
and the AI grammar corrected.

### Models & tools

- GLM-5.3-Flash (opencode): Plan and implement the whole sac-strike
  assignment (etcdapi.py, the strike mode of app.py, docker-compose.yml,
  strike-demo and the READMEs of both repositories), also needed modifications
  to sac-restad.
