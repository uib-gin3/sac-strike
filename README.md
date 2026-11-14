# The calculators' **strike**

Send calculations, caculators will elect a lead that will lead by example
doing the work as well as delegating part of it.

Leaders burnout so they step down and a new leader is elected.
Sometimes other calculators also step down going on strike and have a tea.

Alegory of how IT companies works, leading usually does not releaf you for
your revious dutties so you burn out. When delegation fasters workers
trend to be punished with more work and also any leaders knows when a
reliable work need to be done who is the right candidate.

## Abstract

An exercice of a distributed system based on the rest calculator 
[sac-restad](https://github.com/uib-gin3/sac-restad) that has been
modified to be used also as a distributed system.

This repo [sac-strike](https://github.com/uib-gin3/sac-strike) deploys
sac-restad in a distributed way. Also includes scripts to test it, mostly
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

Start the workers (like a `docker compose up` with some asteriods)

    ./strike-up

Wait for a leader to be elected, returns when ready

    ./strike-ready

Test a calculation `strike-leader` returns the enpoint then curl it.

    ID=$(curl -s -X POST $(./strike-leader)/calc --data-binary 3,4,5,6)
    curl -v $(./strike-leader)/calc/$ID/add
    # X-Lead-By: node2         the leader that orchestrated
    # X-Calculated-By: node5   the node that computed
    # 18

There is also a python client to avoid using curl

    ./strike-client -v -o add 3 4 5 6

To know who is the current leader

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
    ./strike-summary -d 60           # Show what appended reading stats
    ./strike-client -o add 3 4 5     # one operation, leader auto-discovered
    docker compose down              # stops everything

They share one clock: strike-demo exports `STRIKE_T0` and every tool
narrates `[xx.xs]` on the same timeline (standalone, they clock
themselves). strike-load keeps its simulated users as internal threads,
just like restad-bench does. (This idea and paragraph was IA generaged,
I'm impressed!)

## Design decisions

Use sac-restad as a base and extend it to be usable as a distributed system
when `` environment variables are present, that way si still compatible
witht the previous use.

Use etcd because is industry standard, high performance and Go developed
wich I prefer over any clucky Java thing.

Minimizing single points of failure that a proxy would introduce,
that is why there is an script that composes the enpoint to use
(`strike-leader`) taking it from etcd (wich is a SPOF itself).

As the client is not inside docker using ports as routing element so the client
can be outside the docker. On a real distributed system DNS would be used.

Using Redis as cache, in this case it could be conidered a SPOF but
it could also be deployed distrubuted but I did not want to overcomplicate
the assingement with it.

Also redis is used to keep statistics.

It would had also been possible to use `etcd` as key-value storage 
and avoid using Redis but I like the idea of keeping `etcd` usage
as minimal as possible as it is critical.

Is true that there can be a gap between asking for the leader and 
sending the request. If done manually can fail that's why there is
`strike-client` that handles those errors and retries.

The leader does some part of the job and delegate other. The propition
of how much calculations are done by the leader vs the delegate ones
are controled by the STRIKE_LEADING_OVERHEAD envvar. The idea is to 
distribute evenly the workload across all the nodes incluing the leader
but as the leader has come overhead coorinating reduce the probability
of doint the job considering this overhead.

The formula is

    1/N - (1/N) * STRIKE_LEADING_OVERHEAD

Assuming a 10% of overhead for being a leader and 5 nodes the probabilty
for the leader to take a calculation would be 18% so 2% as leader job,
probalbly not enough that why they burnout ;)

How the work is delegated to the other workers is controled by
`STRIKE_ALGORITHM` envvar bein possible 3 algorithims:

- `random`: just as random as it sound
- `robust`: preference for reliable workers that failed less
- `fastest`: preferece for faster workers 

Both `robust` and `fastest` uses statistics stored on Redis to have
the values.

The nodes register themselfs at the etcd when staring up so the system
auto-scales. 

Leaders burnsout forcing a new leader to be elected.

Workers go on strike provking the leader leader to fail and taking that into
acount agains their robustness that may be relevant if is the sued algorithm.

A caos monkey is implemented to push workers into strike.


### Leadership election on etcd

TODO

## Observations

With the default 2-6s strikes every 4-9s and 8-20s burnout countdowns,
expect roughly one leadership transition every ~10s and a node on strike
~25% of the time. The 5-retry delegation absorbs most of it: the summary
usually shows a handful of teapots (the seconds where the old leader answers
418 before etcd has a new leader) and very few 5xx.

The delegation algorithm changes the failure profile of the same 30s run
(same chaos, ~1300 requests):

## Intresting future works

Would be great do play and do simulations to see wich delegation algorithm
works best on different parameters and caos situations.


## AI usage

As I had to miss some clases about the topic I've followed a different
approach as previus assingments. In this one I've tried to promt what
I wanted giving access to the lessons to the AI agent and it implemented
crucial modifications of sac-restad to be distributed as well as configuring etcd.

The used prompts can be found at PROMPT.md

Initially this README as AI generated but I've rewritten it to be simplified
and the AI gammar corrected.

### Models & tools

- GLM-5.3-Flash (opencode): Plan and implement the whole sac-strike
  assignment (etcdapi.py, the strike mode of app.py, docker-compose.yml,
  strike-demo and the READMEs of both repositories) also needed modificatios
  on sac-restad.
