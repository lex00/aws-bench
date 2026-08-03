# Questions aws-bench does not ask

Two introspection questions of a shape the upstream set contains exactly one of.
They are not aws-bench's. They are ours, and anything published from them has to
say so.

## Why these two

`list-unused-security-groups-all-regions` is the most interesting result on the
board and the least representative. Across every valid run:

| arm | gets it |
|---|--:|
| chant | 51% |
| No tool (AWS CLI) | 28% |
| Alchemy | 5% |
| Pulumi, Terraform, AWS CDK | **0 of 66** |

Every arm that keeps a state file is at zero, and an agent with no
infrastructure tooling beats all three of them. The explanation is structural
rather than incidental: the answer is a negative about things a state file does
not contain. Four groups are attached to nothing, so nothing the tool created
references them, and reading your own state cannot find what nothing points at.

That is one question out of eight. One question is an anecdote, and the whole
result currently rests on it — so the question worth asking is whether the
finding is about the *shape* or about that one question.

## The two

| task | the negative | today's answer |
|---|---|--:|
| `subnets-with-no-network-interfaces` | subnets nothing occupies | 8 of 13 |
| `vpcs-with-no-running-instances` | VPCs running nothing | 2 of 6 |

Both share the property that makes the security-group question hard. The
account's default VPCs and their subnets were created by no deployment, so an
arm reading only its own state sees a subset and cannot know what it is missing.

Neither is a gimme for chant. It scores about half on the existing question of
this shape, and there is no reason to expect better here.

## The conditions these were written under

**Written before any arm ran them.** The estate was queried to check the answers
are non-trivial — a question whose answer is "none" measures nothing — and then
the tasks were written. Nothing was tuned to a result, because there were no
results.

**Five other candidates were discarded**, because the estate does not support
them: unattached network interfaces (0), route tables with no association (0),
security groups referenced only by other groups (0), unattached volumes (0), and
security groups with no ingress rules (7 of 8, which is "almost all of them" and
so discriminates nothing). Recorded here because the ones that survived look
cherry-picked without the ones that did not.

**Published either way.** A question set added by the author of one of the tools
is worth nothing unless the arm that author builds can lose on it. chant's score
on these goes on the site whatever it is.

**Scored separately.** The eight-question board is over eight questions. Folding
two more in would silently change every arm's denominator and make the new
numbers incomparable with the published ones. These get their own set.

## Ground truth

Computed live by each task's `pre_invoke.py`, sweeping the account at run time
and substituting the result into the reference answer. The estate is redeployed
before every run with fresh resource ids, so a written-down count would track
the scenario only until someone edited it. Verified against the deployed estate:
8 empty subnets (us-east-1: 2, us-west-1: 3, us-west-2: 3) and 2 empty VPCs of 6.

## Running them

```sh
./benchmarks/agent-env/run-arm.sh chant          # deploy the estate, score the eight
./benchmarks/agent-env/run-negatives.sh chant    # score these two on the same estate
```

`run-negatives.sh` neither wipes nor deploys — it scores whatever is up, so the
estate has to be the one that arm deployed. The estate gate runs first for that
reason.
