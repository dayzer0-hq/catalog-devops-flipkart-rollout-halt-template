# Flipkart checkout — deploy a broken image on purpose and prove the rollout halted

Two image tags from one codebase:

| tag | behaviour |
|---|---|
| `checkout:good` | warms up for 3 seconds, then `/readyz` 200 and `/checkout` serves |
| `checkout:broken` | starts, stays alive, `/readyz` **never** returns 200 |

Both are this repository: `Dockerfile` builds the good one, `Dockerfile.broken` builds the
broken one by baking `BREAK_READINESS=1`.

## Build both and load them into a local cluster

    kind create cluster --name dz0
    docker build -t checkout:good -f Dockerfile .
    docker build -t checkout:broken -f Dockerfile.broken .
    kind load docker-image checkout:good checkout:broken --name dz0

## How to watch a rollout, and how to roll one back

    kubectl apply -f k8s/deployment.yaml
    kubectl rollout status deployment/checkout --timeout=60s

    # deploy the broken tag
    kubectl set image deployment/checkout checkout=checkout:broken
    kubectl rollout status deployment/checkout --timeout=60s   # this should NOT succeed
    kubectl get pods -l app=checkout

    # put it back
    kubectl rollout undo deployment/checkout

## What is deliberately wrong in `k8s/deployment.yaml`

There is **no `readinessProbe`**, so a pod counts as available as soon as it starts. Deploy the
broken tag against this manifest and the rollout completes "successfully" while no pod can
serve. Adding the probe is what makes the halt possible; `maxUnavailable` is what guarantees
the old pods keep serving while it halts.
